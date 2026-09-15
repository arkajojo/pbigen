"""Bring-your-own-model backend via LiteLLM.

LiteLLM gives one interface to ~100 providers, so the same code targets a hosted API
(OpenAI, Anthropic, Gemini) or a local open-source model (Ollama, vLLM, LM Studio) — you
choose with ``model=`` and the matching credentials/endpoint in the environment.

The model only ever sees *metadata*: column names, canonical types and approximate distinct
counts. No row data is sent. If the model is unreachable or returns something unusable, we fall
back to the deterministic design so generation never hard-fails.

Author: Arka Gupta
"""
from __future__ import annotations

import json
from typing import Any

from ..core.design import Design, Measure, Page, Visual
from ..core.design import design as _baseline
from ..core.schema import Schema
from .base import Model

_ALLOWED_VISUALS = {
    "card", "kpi", "line", "area", "column", "columnStacked", "bar", "barStacked",
    "donut", "pie", "scatter", "table", "matrix", "slicer",
}

_SYSTEM = (
    "You are a senior BI designer. Given a table's metadata (column names, canonical types, "
    "approximate distinct-value counts) and an objective, design a clear, executive-grade "
    "dashboard. Reason about DATA SHAPE: use a date/time column as a range filter (never a "
    "dropdown of hundreds of values); use a donut only for <=8 categories, otherwise a bar; put "
    "wide breakdowns in a matrix or table; lead each page with KPI cards. Return ONLY JSON."
)

_SCHEMA_INSTRUCTIONS = """
Return a single JSON object:
{
  "measures": [
    {"name": "Total Revenue", "column": "revenue", "agg": "SUM", "money": true}
  ],
  "pages": [
    {"name": "Executive Summary",
     "slicers": ["order_date", "region"],
     "visuals": [
       {"type": "card", "title": "Total Revenue", "measures": ["Total Revenue"]},
       {"type": "line", "title": "Revenue over time", "measures": ["Total Revenue"], "category": "order_date"},
       {"type": "bar", "title": "Revenue by region", "measures": ["Total Revenue"], "category": "region"}
     ]}
  ],
  "usage_notes": ["Use the left filters to focus the report."]
}
Valid visual types: card, kpi, line, area, column, columnStacked, bar, barStacked, donut, pie,
scatter, table, matrix. Measures reference names from the "measures" list. category/series/columns
reference real column names. Keep 3-4 pages telling a summary -> trends -> segmentation -> detail story.
"""


class LiteLLMModel(Model):
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2,
                 api_key: str | None = None, api_base: str | None = None,
                 max_tokens: int = 4000, **extra: Any):
        self.model = model
        self.name = f"litellm:{model}"
        self.temperature = temperature
        self.api_key = api_key
        self.api_base = api_base
        self.max_tokens = max_tokens
        self.extra = extra

    def design(self, schema: Schema, objective: str) -> Design:
        baseline = _baseline(schema, objective)
        try:
            raw = self._complete(self._prompt(schema, objective))
            parsed = _parse(raw, schema, baseline)
            return parsed or baseline
        except Exception as exc:  # noqa: BLE001 - never let the model break generation
            import sys
            print(f"pbigen: model '{self.model}' did not run ({type(exc).__name__}: "
                  f"{str(exc)[:200]}); falling back to the deterministic design.", file=sys.stderr)
            return baseline

    def _prompt(self, schema: Schema, objective: str) -> str:
        cols = "\n".join(
            f"- {c.name}: {c.dtype}" + (f" (~{c.cardinality} distinct)" if c.cardinality is not None else "")
            for c in schema.columns
        )
        return (
            f"Table: {schema.table}\nObjective: {objective or 'general executive overview'}\n\n"
            f"Columns:\n{cols}\n{_SCHEMA_INSTRUCTIONS}"
        )

    def _complete(self, user_prompt: str) -> str:
        import litellm
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": user_prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        kwargs.update(self.extra)
        resp = litellm.completion(**kwargs)
        return resp["choices"][0]["message"]["content"]


def _parse(raw: str, schema: Schema, baseline: Design) -> Design | None:
    """Parse the model's JSON into a Design, keeping only references that exist in the schema."""
    data = _extract_json(raw)
    if not isinstance(data, dict) or not data.get("pages"):
        return None
    colnames = set(schema.names())

    measures: list[Measure] = []
    for m in data.get("measures", []):
        if not isinstance(m, dict) or not m.get("name"):
            continue
        measures.append(Measure(
            name=str(m["name"]),
            kind=str(m.get("kind", "agg")),
            column=m.get("column"),
            agg=str(m.get("agg", "SUM")).upper(),
            numerator=m.get("numerator"),
            denominator=m.get("denominator"),
            dimension=m.get("dimension"),
            money=bool(m.get("money", False)),
            percent=bool(m.get("percent", False)),
        ))
    if not measures:
        measures = baseline.measures
    measure_names = {m.name for m in measures}

    def valid_cols(names: Any) -> list[str]:
        return [c for c in (names or []) if c in colnames]

    pages: list[Page] = []
    for p in data.get("pages", []):
        if not isinstance(p, dict):
            continue
        visuals: list[Visual] = []
        for v in p.get("visuals", []):
            if not isinstance(v, dict) or v.get("type") not in _ALLOWED_VISUALS:
                continue
            cat = v.get("category") if v.get("category") in colnames else None
            ser = v.get("series") if v.get("series") in colnames else None
            ms = [m for m in (v.get("measures") or []) if m in measure_names]
            visuals.append(Visual(
                type=str(v["type"]),
                title=str(v.get("title", "")),
                measures=ms,
                category=cat,
                series=ser,
                columns=valid_cols(v.get("columns")),
                x_measure=v.get("x_measure") if v.get("x_measure") in measure_names else None,
                y_measure=v.get("y_measure") if v.get("y_measure") in measure_names else None,
                size_measure=v.get("size_measure") if v.get("size_measure") in measure_names else None,
            ))
        if not visuals:
            continue
        slicers = valid_cols(p.get("slicers"))
        pages.append(Page(name=str(p.get("name", "Page")), visuals=visuals, slicers=slicers))

    if not pages:
        return None
    notes = [str(n) for n in data.get("usage_notes", []) if str(n).strip()] or baseline.usage_notes
    return Design(measures=measures, pages=pages, usage_notes=notes,
                  rationale="LLM-designed, validated against the live schema.")


def _extract_json(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
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
