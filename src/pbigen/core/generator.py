"""The generator: source -> schema+cardinality -> design -> Power BI project.

This is the one function that stitches the pieces together. It stays thin on purpose — all the
judgement lives in the source adapters, the design model and the emitter — so the pipeline is easy
to read and to test end to end.

Author: Arka Gupta
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Model, get_model
from ..sources import Source, get_source
from ..themes import get_theme, split_chrome
from .design import Design


@dataclass
class GenerateResult:
    pbip_path: str
    design: Design
    table: str
    n_columns: int
    n_pages: int
    model_name: str


def _project_name(raw: str) -> str:
    name = re.sub(r"[^0-9A-Za-z_-]+", "-", raw).strip("-")
    return name or "dashboard"


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
) -> GenerateResult:
    """Generate a Power BI project from a source.

    ``source`` may be a configured :class:`Source` or a kind string (with ``source_config``).
    ``model`` may be a :class:`Model`, a LiteLLM model id, or ``None`` for the deterministic design.
    ``theme`` may be a built-in name or a path to a Power BI theme JSON.
    """
    src = source if isinstance(source, Source) else get_source(source, **(source_config or {}))
    mdl = model if isinstance(model, Model) else get_model(model, **(model_config or {}))

    schema = src.schema_with_cardinality()
    design = mdl.design(schema, objective)
    theme_doc, sidebar, accent = split_chrome(get_theme(theme))

    # Report the model honestly: an LLM that fails is caught and falls back to the deterministic
    # design — say so rather than pretending the LLM ran.
    model_name = mdl.name
    if mdl.name != "deterministic" and not design.rationale.lower().startswith("llm"):
        model_name = f"deterministic (fallback — {mdl.name} did not run; check the model id / credentials)"

    from ..emit import write_project
    project = name or _project_name(schema.display_name or schema.table)
    pbip_path = write_project(
        design, schema, src.power_query(), out_dir, project,
        theme=theme_doc, sidebar_color=sidebar, accent=accent,
        brand=schema.display_name, mode=mode,
        nav_side=("right" if str(nav).lower().startswith("r") else "left"), logo=logo,
    )
    return GenerateResult(
        pbip_path=pbip_path, design=design, table=schema.table,
        n_columns=len(schema.columns), n_pages=len(design.pages), model_name=model_name,
    )
