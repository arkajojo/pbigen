"""The generator: source -> schema (+cardinality, +profile) -> design -> Power BI project.

This is the one function that stitches the pieces together. It stays thin on purpose — all the
judgement lives in the source adapters, the design model/pipeline and the emitter — so the flow
is easy to read and to test end to end:

1. introspect the source (metadata + approximate distinct counts; aggregate profile if asked),
2. add a monthly time grain so trends read by month,
3. design: deterministic storyboard, or the staged LLM pipeline (context -> objectives ->
   research -> storyboard -> critique),
4. finish: period-over-period deltas on every KPI card, an "About this report" page,
5. emit into pbigen's shell, or into a **template pack** built from the customer's own report.

Author: Arka Gupta
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

from ..ai.pipeline import DesignRequest
from ..models import Model, get_model
from ..sources import Source, get_source
from ..themes import get_theme, split_chrome
from .design import Design, add_about_page, add_comparisons, primary_date
from .schema import with_time_grain


@dataclass
class GenerateResult:
    pbip_path: str
    design: Design
    table: str
    n_columns: int
    n_pages: int
    model_name: str
    design_md: str = ""
    template: str | None = None


def _project_name(raw: str) -> str:
    name = re.sub(r"[^0-9A-Za-z_-]+", "-", raw).strip("-")
    return name or "dashboard"


def _read_context(context: str) -> str:
    """``context`` may be text or a path to a file (a brief, a README, meeting notes …)."""
    if context and len(context) < 1024 and os.path.isfile(context):
        with open(context, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()[:12000]
    return context or ""


def _call_design(mdl: Model, schema, objective: str, request: DesignRequest) -> Design:
    """Call ``mdl.design`` — with the request when the model accepts it (0.4+), without it for
    custom models written against the 0.3 ``design(schema, objective)`` signature."""
    import inspect
    try:
        params = inspect.signature(mdl.design).parameters
    except (TypeError, ValueError):
        params = {}
    takes_request = "request" in params or len(params) >= 3 or any(
        p.kind is inspect.Parameter.VAR_POSITIONAL for p in params.values())
    return mdl.design(schema, objective, request) if takes_request else mdl.design(schema, objective)


def generate(
    source: Source | str,
    *,
    out_dir: str = "out",
    name: str | None = None,
    objective: str = "",
    model: Model | str | None = None,
    theme: str | None = None,
    mode: str = "import",
    nav: str = "left",
    logo: str | None = None,
    source_config: dict | None = None,
    model_config: dict | None = None,
    template: str | None = None,
    context: str = "",
    audience: str = "",
    profile: bool = False,
    research: str = "builtin",
    critique: bool = True,
    compare_days: int = 30,
) -> GenerateResult:
    """Generate a Power BI project from a source.

    ``source`` may be a configured :class:`Source` or a kind string (with ``source_config``).
    ``model`` may be a :class:`Model`, a LiteLLM model id, or ``None`` for the deterministic design.
    ``theme`` may be a built-in name or a path to a Power BI theme JSON.
    ``template`` may be a template-pack folder or a report file (``.pbix``/``.pbit``/``.pbip``) —
    the new dashboard is rendered inside that report's design.
    ``context`` is business context as text or a file path; ``profile`` sends aggregate value
    profiles (never rows) to the model; ``research`` is ``builtin``, ``web`` or ``off``.
    """
    src = source if isinstance(source, Source) else get_source(source, **(source_config or {}))
    mdl = model if isinstance(model, Model) else get_model(model, **(model_config or {}))

    if logo and not os.path.exists(logo):
        print(f"pbigen: --logo file not found, skipping: {logo}", file=sys.stderr)
        logo = None

    schema = src.schema_with_cardinality()
    if profile:
        try:
            schema.profile = src.profile(schema) or {}
        except Exception as exc:  # noqa: BLE001 - profiling is optional
            print(f"pbigen: profiling skipped ({type(exc).__name__}: {str(exc)[:120]})", file=sys.stderr)
    schema = with_time_grain(schema, primary_date(schema), mode)

    request = DesignRequest(objective=objective or "", context=_read_context(context),
                            research=(research or "builtin").lower(), audience=audience or "",
                            critique=critique)
    design = _call_design(mdl, schema, objective, request)
    design = add_comparisons(design, schema, compare_days)
    design = add_about_page(design, schema, source_label=getattr(src, "kind", "") + f": {schema.table}")

    # Report the model honestly: an LLM that fails falls back to the deterministic design — say so
    # rather than pretending the LLM ran.
    model_name = mdl.name
    if mdl.name != "deterministic" and not design.rationale.lower().startswith("llm"):
        model_name = f"deterministic (fallback — {mdl.name} did not produce a valid design; see messages above)"

    project = name or _project_name(schema.display_name or schema.table)

    pack = None
    if template:
        from ..template import resolve_template
        work = None
        if not os.path.isdir(template):
            stem = _project_name(os.path.splitext(os.path.basename(template.rstrip("/")))[0])
            work = os.path.join(out_dir, f".pbigen-template-{stem}")
        pack = resolve_template(template, work_dir=work)

    if theme:
        theme_doc, sidebar, accent = split_chrome(get_theme(theme))
    elif pack is not None:
        pt = pack.theme()
        theme_doc, sidebar, accent = (split_chrome(pt) if pt else (None, "#1B1F3B", "#FFFFFF"))
    else:
        theme_doc, sidebar, accent = split_chrome(get_theme(None))

    from ..emit import write_project
    pbip_path = write_project(
        design, schema, src.power_query(), out_dir, project,
        theme=theme_doc, sidebar_color=sidebar, accent=accent,
        brand=schema.display_name, mode=mode,
        nav_side=("right" if str(nav).lower().startswith("r") else "left"), logo=logo,
        template=pack,
    )
    return GenerateResult(
        pbip_path=pbip_path, design=design, table=schema.table,
        n_columns=len(schema.source_columns()), n_pages=len(design.pages), model_name=model_name,
        design_md=os.path.join(os.path.dirname(pbip_path), "DESIGN.md"),
        template=(pack.name if pack else None),
    )
