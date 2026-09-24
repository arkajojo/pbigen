"""The staged AI design pipeline: context -> objectives -> research -> storyboard -> critique.

Each stage is one LLM call with its own expert persona, the curated knowledge base and a strict
JSON contract; later stages see everything earlier stages concluded. The final design is parsed
and **validated against the live schema** (unknown columns, undefined measures, charts that do not
fit the data shape are repaired or dropped), so a model can never emit a report that breaks in
Power BI. Any stage can fail without sinking the run: context/objectives/research degrade to the
built-in playbooks, and if no valid design emerges the deterministic design is returned.

Only metadata leaves the machine — column names, types, distinct counts — plus aggregate value
profiles (min/max/top values) when the user opts in with ``--profile``.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

from ..core.design import SIZES, Design, Measure, Page, Visual
from ..core.design import design as baseline_design
from ..core.schema import DATE, DATETIME, Schema, month_column_name
from . import prompts as P
from .knowledge import design_handbook, infer_playbook

ALLOWED_VISUALS = {
    "card", "kpi", "line", "area", "column", "columnStacked", "bar", "barStacked", "combo",
    "waterfall", "donut", "pie", "treemap", "scatter", "table", "matrix",
}
_AGGS = {"SUM", "AVERAGE", "MIN", "MAX", "COUNT", "DISTINCTCOUNT"}


@dataclass
class DesignRequest:
    """What the user tells pbigen about the dashboard (all optional)."""

    objective: str = ""
    context: str = ""            # business brief: who, what, why (free text or a file's content)
    research: str = "builtin"    # builtin | web | off
    audience: str = ""
    critique: bool = True


Complete = Callable[..., str]    # complete(system, user, web=False) -> str


# --------------------------------------------------------------------------- helpers
def describe_schema(schema: Schema) -> str:
    lines = [f"Table: {schema.table}" + (f" ({schema.display_name})" if schema.display_name else "")]
    lines.append("Columns (name: type [~distinct values] {profile}):")
    for c in schema.columns:
        s = f"- {c.name}: {c.dtype}"
        if c.cardinality is not None:
            s += f" [~{c.cardinality} distinct]"
        if c.expression:
            s += " (model-calculated monthly grain of the date — use it as the axis for trends)"
        prof = schema.profile.get(c.name)
        if prof:
            s += " " + json.dumps(prof, default=str)[:300]
        lines.append(s)
    return "\n".join(lines)


def extract_json(raw: str) -> Any:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lstrip().startswith("json"):
            raw = raw.lstrip()[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _log(msg: str) -> None:
    print(f"pbigen ▸ {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- validation
def parse_design(data: Any, schema: Schema, baseline: Design) -> Design | None:
    """Turn a model's design JSON into a :class:`Design`, keeping only what is valid for ``schema``."""
    if not isinstance(data, dict) or not data.get("pages"):
        return None
    colnames = set(schema.names())
    card = {c.name: c.cardinality for c in schema.columns}
    dates = {c.name for c in schema.columns if c.dtype in (DATE, DATETIME)}

    # ---- measures (two passes: aggregates first, then divides that reference them) ----
    measures: list[Measure] = []
    raw_ms = [m for m in data.get("measures", []) if isinstance(m, dict) and m.get("name")]
    pending_divides = []
    seen: set[str] = set()
    for m in raw_ms:
        name = str(m["name"]).strip()[:80]
        if not name or name in seen:
            continue
        kind = str(m.get("kind", "agg")).lower()
        agg = str(m.get("agg", "SUM")).upper()
        col = m.get("column")
        num, den = m.get("numerator"), m.get("denominator")
        unit = str(m.get("unit", "")).lower()
        common = dict(money=bool(m.get("money")) or unit == "money",
                      percent=bool(m.get("percent")) or unit == "percent",
                      higher_is_better=m.get("higher_is_better", True) is not False,
                      description=str(m.get("description") or m.get("definition") or "")[:300])
        if kind in ("divide", "add", "subtract", "multiply"):
            pending_divides.append((name, kind, num, den, common))
            continue
        # Drop measures that reference columns which don't exist — otherwise the generated DAX is
        # invalid and the visual errors in Power BI ("Something's wrong with one or more fields").
        if kind == "ratio":
            if num not in colnames or den not in colnames:
                continue
        elif agg not in _AGGS:
            continue
        elif agg in ("COUNT", "DISTINCTCOUNT"):
            col = col if col in colnames else None      # count works with or without a column
            if agg == "DISTINCTCOUNT" and col is None:
                continue
        elif col not in colnames:                        # SUM/AVERAGE/MIN/MAX need a real column
            continue
        measures.append(Measure(name=name, kind="ratio" if kind == "ratio" else "agg", column=col, agg=agg,
                                numerator=num, denominator=den, dimension=m.get("dimension"), **common))
        seen.add(name)
    # KPI-on-KPI formulas may reference each other: resolve until nothing new validates
    progress = True
    while pending_divides and progress:
        progress = False
        for item in list(pending_divides):
            name, kind, num, den, common = item
            if num in seen and den in seen and name not in seen:
                measures.append(Measure(name=name, kind=kind, numerator=num, denominator=den, **common))
                seen.add(name)
                pending_divides.remove(item)
                progress = True
    if not measures:
        measures = list(baseline.measures)
    mnames = {m.name for m in measures}

    def col_ok(c: Any) -> str | None:
        return c if isinstance(c, str) and c in colnames else None

    def month_of(c: str | None) -> str | None:
        """Trends on a raw timestamp are unreadable: use the monthly grain when the model has it."""
        if c in dates and month_column_name(c) in colnames:
            return month_column_name(c)
        return c

    # ---- pages ----
    pages: list[Page] = []
    for p in data.get("pages", []):
        if not isinstance(p, dict):
            continue
        if "about" in str(p.get("name", "")).lower():
            continue                                     # the engine builds the About page itself
        visuals: list[Visual] = []
        for v in p.get("visuals", []):
            if not isinstance(v, dict):
                continue
            vt = v.get("type")
            if vt not in ALLOWED_VISUALS:
                continue
            ms = [x for x in (v.get("measures") or []) if x in mnames]
            lines = [x for x in (v.get("line_measures") or []) if x in mnames]
            cat, ser = col_ok(v.get("category")), col_ok(v.get("series"))
            cols = [c for c in (v.get("columns") or []) if c in colnames][:8]
            xm = v.get("x_measure") if v.get("x_measure") in mnames else None
            ym = v.get("y_measure") if v.get("y_measure") in mnames else None
            sm = v.get("size_measure") if v.get("size_measure") in mnames else None
            if vt in ("line", "area", "combo", "columnStacked") and cat:
                cat = month_of(cat)
            # repair shape mismatches instead of emitting a broken or unreadable visual
            if ser and (card.get(ser) or 0) > (50 if vt == "treemap" else 6):
                ser = None
            if vt in ("donut", "pie") and cat and (card.get(cat) or 10_000) > 6:
                vt = "bar"
            if vt == "combo" and not lines:
                vt = "column"
            if vt == "combo" and not ms and lines:
                ms, lines = lines[:1], lines[1:]
            if vt in ("columnStacked", "barStacked") and not ser:
                vt = "column" if vt == "columnStacked" else "bar"
            if vt == "scatter":
                xm = xm or (ms[0] if ms else None)
                ym = ym or (ms[1] if len(ms) > 1 else None)
                if not (xm and ym and cat):
                    continue
            elif vt in ("card", "kpi"):
                if not ms:
                    continue
                ms = ms[:1]
            elif vt == "table":
                if not cols and not ms:
                    continue
            elif vt == "matrix":
                if not ms or not cat:
                    continue
            elif not ms or not cat:
                continue                                 # a chart without a measure and axis is empty
            size = v.get("size") if v.get("size") in SIZES else ""
            visuals.append(Visual(
                type=vt, title=str(v.get("title", ""))[:120], subtitle=str(v.get("subtitle", ""))[:220],
                measures=ms, line_measures=lines[:2], category=cat, series=ser, columns=cols,
                x_measure=xm, y_measure=ym, size_measure=sm, size=size,
                sort_desc=bool(v.get("sort_desc")), labels=bool(v.get("labels")),
            ))
        if not visuals:
            continue
        slicers = []
        for s in p.get("slicers") or []:
            if s in colnames and s not in slicers and (s in dates or (card.get(s) or 0) <= 50):
                slicers.append(s)
        pages.append(Page(name=str(p.get("name", "Page"))[:60], visuals=visuals, slicers=slicers[:5],
                          question=str(p.get("question", ""))[:200]))

    if not pages:
        return None
    notes = [str(n) for n in data.get("usage_notes", []) if str(n).strip()][:4] or baseline.usage_notes
    return Design(measures=measures, pages=pages, usage_notes=notes,
                  rationale="LLM-designed, validated against the live schema.")


# --------------------------------------------------------------------------- the pipeline
class DesignPipeline:
    def __init__(self, complete: Complete, model_name: str, verbose: bool = True):
        self.complete = complete
        self.model_name = model_name
        self.verbose = verbose
        self.stages: list[dict] = []

    def _stage(self, n: int, total: int, label: str, fn: Callable[[], Any]) -> Any:
        t0 = time.time()
        if self.verbose:
            _log(f"{n}/{total} {label} …")
        try:
            out = fn()
            status = "ok" if out is not None else "empty"
        except Exception as exc:  # noqa: BLE001 - a stage failing must never sink the run
            out, status = None, f"failed ({type(exc).__name__}: {str(exc)[:160]})"
        secs = round(time.time() - t0, 1)
        self.stages.append({"stage": label, "status": status, "note": f"{secs}s"})
        if self.verbose:
            _log(f"{n}/{total} {label}: {status} ({secs}s)")
        return out

    def _json_call(self, system: str, user: str, web: bool = False) -> Any:
        raw = self.complete(system, user, web=web)
        data = extract_json(raw)
        if data is None:
            raw = self.complete(system, user + "\n\n" + P.REPAIR.format(error="unparseable"), web=False)
            data = extract_json(raw)
        return data

    def run(self, schema: Schema, request: DesignRequest) -> Design:
        baseline = baseline_design(schema, request.objective, context=request.context)
        playbook = infer_playbook(schema.names(), f"{request.objective} {request.context} {schema.table}")
        cols = describe_schema(schema)
        brief_user = (f"User objective: {request.objective or '(none given — infer the most valuable one)'}\n"
                      f"User business context: {request.context or '(none given)'}\n"
                      f"Intended audience: {request.audience or '(infer)'}\n")
        total = 5 if request.critique else 4
        if request.research == "off":
            total -= 1
        n = 0

        # 1) business context
        n += 1
        ctx = self._stage(n, total, "business context", lambda: self._json_call(
            P.CONTEXT_SYSTEM,
            f"{brief_user}\nLikely domain (keyword match, verify it): {playbook.name}\n\n{cols}\n\n{P.CONTEXT_CONTRACT}"))
        ctx = ctx if isinstance(ctx, dict) else {}

        # 2) objectives + KPI tree
        n += 1
        obj = self._stage(n, total, "objectives & KPI tree", lambda: self._json_call(
            P.OBJECTIVES_SYSTEM,
            f"{brief_user}\nBusiness context (stage 1):\n{json.dumps(ctx, indent=1)[:6000]}\n\n"
            f"{playbook.as_text()}\n\n{cols}\n\n{P.OBJECTIVES_CONTRACT}"))
        obj = obj if isinstance(obj, dict) else {}

        # 3) research
        research: dict = {}
        if request.research != "off":
            n += 1
            research = self._stage(n, total, f"research ({request.research})",
                                   lambda: self._research(request, ctx, obj, playbook)) or {}

        # 4) storyboard
        n += 1
        context_pack = (f"{brief_user}\nBusiness context:\n{json.dumps(ctx, indent=1)[:6000]}\n\n"
                        f"Objectives & KPI tree:\n{json.dumps(obj, indent=1)[:8000]}\n\n"
                        f"Research:\n{json.dumps(research, indent=1)[:5000]}\n\n{playbook.as_text()}\n\n{cols}")
        draft = self._stage(n, total, "storyboard & visual design", lambda: self._json_call(
            P.STORYBOARD_SYSTEM, f"{context_pack}\n\n{P.STORYBOARD_CONTRACT}"))
        design = parse_design(draft, schema, baseline) if draft else None

        # 5) critique & repair
        issues: list = []
        if request.critique and design is not None:
            n += 1
            review = self._stage(n, total, "design critique & repair", lambda: self._json_call(
                P.CRITIQUE_SYSTEM,
                f"{context_pack}\n\nDRAFT DESIGN:\n{json.dumps(draft, indent=1)[:14000]}\n\n{P.CRITIQUE_CONTRACT}"))
            if isinstance(review, dict):
                issues = review.get("issues") or []
                revised = parse_design(review.get("design"), schema, baseline)
                if revised is not None:
                    design = revised

        if design is None:
            if self.verbose:
                _log("no valid LLM design — using the deterministic design (the reasoning above is kept)")
            design = baseline
            design.rationale = "deterministic (fallback — the LLM design did not validate)"
            engine = f"deterministic fallback ({self.model_name})"
        else:
            engine = f"llm pipeline ({self.model_name})"

        design.brief = self._brief(engine, baseline, ctx, obj, research, issues, request, playbook, draft)
        return design

    # -- research ---------------------------------------------------------------
    def _research(self, request: DesignRequest, ctx: dict, obj: dict, playbook) -> dict | None:
        domain = ctx.get("domain") or playbook.name
        objectives = "; ".join(str(o.get("objective", o)) if isinstance(o, dict) else str(o)
                               for o in (obj.get("objectives") or playbook.objectives))[:600]
        seed = (f"Domain: {domain}\nObjectives: {objectives}\n"
                f"KPI tree so far: {json.dumps(obj.get('kpis', []))[:3000]}\n\n"
                f"Curated knowledge to build on:\n{playbook.as_text()}\n\n{design_handbook()}\n\n"
                f"{P.RESEARCH_CONTRACT}")
        if request.research == "web":
            task = P.WEB_RESEARCH_TASK.format(domain=domain, objectives=objectives)
            try:
                data = extract_json(self.complete(P.RESEARCH_SYSTEM, f"{task}\n\n{seed}", web=True))
                if isinstance(data, dict):
                    data["mode"] = "web search"
                    return data
            except Exception as exc:  # noqa: BLE001 - web search is best-effort
                if self.verbose:
                    _log(f"web research unavailable for this model ({type(exc).__name__}); "
                         "using built-in research")
        data = self._json_call(P.RESEARCH_SYSTEM, seed)
        if isinstance(data, dict):
            data["mode"] = "built-in knowledge" + (" (web unavailable)" if request.research == "web" else "")
        return data

    # -- brief --------------------------------------------------------------------
    def _brief(self, engine, baseline, ctx, obj, research, issues, request, playbook, draft) -> dict:
        b = dict(baseline.brief)
        b["engine"] = engine
        if ctx:
            b["context"] = ctx
            b["domain"] = ctx.get("domain") or b.get("domain")
            b["grain"] = ctx.get("grain") or b.get("grain")
            if ctx.get("audience"):
                b["audience"] = ctx["audience"]
            b["caveats"] = (ctx.get("caveats") or [])[:5]
        if obj:
            ns = obj.get("north_star")
            if ns:
                b["north_star"] = ns.get("name") if isinstance(ns, dict) else ns
            if obj.get("objectives"):
                b["objectives"] = obj["objectives"]
            if obj.get("kpis"):
                b["kpis"] = obj["kpis"]
            b["gaps"] = obj.get("gaps") or []
        objs = b.get("objectives") or []
        first = objs[0] if objs else None
        b["objective"] = (request.objective
                          or (first.get("objective") if isinstance(first, dict) else first)
                          or b.get("objective"))
        if research:
            b["research"] = research
        if issues:
            b["critique"] = issues
        if isinstance(draft, dict) and draft.get("coverage"):
            b["coverage"] = draft["coverage"]
        b["stages"] = self.stages
        return b
