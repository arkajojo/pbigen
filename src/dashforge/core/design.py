"""The design brain: turn a schema + an objective into a logical dashboard design.

This module is deliberately deterministic and dependency-free. It classifies every column
(measure / date / category / geo / id), proposes sensible measures, and lays out a narrative
set of pages whose chart and filter choices are driven by the *data shape* (types and
distinct-value counts). A language model can refine this design (see ``blueprint``), but the
rules here always produce a complete, coherent dashboard on their own.

Author: Arka Gupta
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import DATETIME, NUMERIC_TYPES, Schema

# ---- column-role heuristics -------------------------------------------------
_DATE_HINT = re.compile(r"(date|dttm|_dt$|_ts$|timestamp|period|year_?month|yyyymm|mth|month|year|week|day)", re.I)
_ID_HINT = re.compile(r"(_id$|^id$|_key$|^key$|uuid|guid|_no$|_number$|_code$|licen|plate|nric|phone|email|account)", re.I)
_CAT_HINT = re.compile(r"(type|status|category|categ|segment|brand|region|area|zone|state|country|city|class|mode|method|group|flag|channel|source|reason|gender|shift|company|fleet|product|service|tier|band|level)", re.I)
_GEO_HINT = re.compile(r"(lat|lon|lng|postal|zipcode|geohash)", re.I)
_MONEY_HINT = re.compile(r"(income|fare|cost|amount|amt|revenue|sales|price|fee|levy|charge|value|gmv|spend|profit|margin)", re.I)
# columns that are derived parts of a date — redundant as filters once a real date exists
_PERIOD_PART = re.compile(r"(year|month|week|quarter|day.?of|_dt$|period|_yr$)", re.I)


@dataclass
class Measure:
    """A logical measure: an aggregation of a column, or a ratio/share of other measures.

    The emitter turns these into the target BI expression (e.g. DAX for Power BI)."""

    name: str
    kind: str = "agg"            # agg | ratio | share
    column: str | None = None
    agg: str = "SUM"             # SUM | AVERAGE | MIN | MAX | COUNT | DISTINCTCOUNT
    numerator: str | None = None
    denominator: str | None = None
    dimension: str | None = None
    money: bool = False
    percent: bool = False


@dataclass
class Visual:
    """One visual on a page. Fields not relevant to a type are simply left unset."""

    type: str                    # card|kpi|line|area|column|columnStacked|bar|barStacked|
    #                              donut|pie|scatter|table|matrix|slicer
    title: str = ""
    measures: list[str] = field(default_factory=list)
    category: str | None = None
    series: str | None = None
    columns: list[str] = field(default_factory=list)
    x_measure: str | None = None
    y_measure: str | None = None
    size_measure: str | None = None
    slicer_mode: str = "Dropdown"
    # layout (filled by the layout packer)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    z: int = 0


@dataclass
class Page:
    name: str
    visuals: list[Visual] = field(default_factory=list)
    slicers: list[str] = field(default_factory=list)


@dataclass
class Design:
    measures: list[Measure] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    usage_notes: list[str] = field(default_factory=list)
    rationale: str = ""


def classify(schema: Schema) -> dict[str, list[str]]:
    """Bucket columns into measures / dates / categories / geo / ids."""
    out: dict[str, list[str]] = {"measures": [], "dates": [], "categories": [], "geo": [], "ids": []}
    for c in schema.columns:
        low = c.name.lower()
        if _GEO_HINT.search(low):
            out["geo"].append(c.name)
        elif c.dtype == DATETIME or (_DATE_HINT.search(low) and (c.is_numeric or c.dtype == "string" or c.is_temporal)):
            out["dates"].append(c.name)
        elif _ID_HINT.search(low):
            out["ids"].append(c.name)
        elif c.dtype in NUMERIC_TYPES:
            out["measures"].append(c.name)
        else:
            out["categories"].append(c.name)
    out["categories"].sort(key=lambda n: (0 if _CAT_HINT.search(n.lower()) else 1, len(n)))
    out["dates"].sort(key=lambda n: (0 if _DATE_HINT.search(n.lower()) else 1, len(n)))
    return out


def propose_measures(schema: Schema, limit: int = 6) -> list[Measure]:
    """Synthesise SUM measures from numeric columns when none are supplied."""
    cls = classify(schema)
    out: list[Measure] = []
    for col in cls["measures"][:limit]:
        pretty = "Total " + col.replace("_", " ").title()
        out.append(Measure(pretty, "agg", column=col, agg="SUM", money=bool(_MONEY_HINT.search(col.lower()))))
    return out


def _good_slicer(name: str, schema: Schema, real_dates: set[str]) -> bool:
    if name in real_dates:
        return True
    if real_dates and _PERIOD_PART.search(name):          # redundant with the date range
        return False
    col = schema.by_name(name)
    card = col.cardinality if col else None
    return card is None or card <= 50                     # dropdowns only for low-cardinality


def design(schema: Schema, objective: str = "", measures: list[Measure] | None = None) -> Design:
    """Deterministic, cardinality-aware dashboard design (the always-on baseline)."""
    cls = classify(schema)
    real_dates = {c.name for c in schema.columns if c.dtype == DATETIME}
    measures = measures or propose_measures(schema)
    headline = [m.name for m in measures][:6] or ["(no measure)"]
    lead = headline[0]

    date = cls["dates"][0] if cls["dates"] else None
    dims = [d for d in cls["categories"]][:4]
    dim0 = dims[0] if dims else None
    dim1 = dims[1] if len(dims) > 1 else None

    def low_card(col: str | None) -> bool:
        c = schema.by_name(col) if col else None
        return bool(col) and (c is None or c.cardinality is None or c.cardinality <= 8)

    def breakdown(metric: str, dim: str, title: str) -> Visual:
        # donut only for few categories, else a bar chart
        return Visual("donut" if low_card(dim) else "bar", title, measures=[metric], category=dim)

    slicers = [s for s in ([date] if date else []) + dims if _good_slicer(s, schema, real_dates)][:5]
    pages: list[Page] = []

    # 1) Executive Summary
    v = [Visual("card", m, measures=[m]) for m in headline[:4]]
    if date:
        v.append(Visual("line", f"{lead} over time", measures=headline[:2], category=date))
    if dim0:
        v.append(breakdown(lead, dim0, f"{lead} by {dim0}"))
    if dim1:
        v.append(breakdown(lead, dim1, f"{lead} by {dim1}"))
    pages.append(Page("Executive Summary", v, slicers))

    # 2) Trends over time
    if date:
        v = [Visual("card", m, measures=[m]) for m in headline[:3]]
        v.append(Visual("line", f"{lead} trend", measures=headline[:3], category=date))
        if dim0:
            v.append(Visual("column", f"{lead} by {dim0}", measures=headline[:2], category=dim0, series=dim1))
        pages.append(Page("Trends Over Time", v, slicers))

    # 3) Segmentation & drivers
    if dim0:
        v = [Visual("column", f"{lead} by {dim0}", measures=[lead], category=dim0)]
        if dim1:
            v.append(Visual("bar", f"{lead} by {dim1}", measures=[lead], category=dim1))
        v.append(Visual("matrix", f"{dim0} × measures", measures=headline, category=dim0, series=dim1))
        pages.append(Page("Segmentation & Drivers", v, slicers))

    # 4) Detail / self-serve
    detail_cols = ([date] if date else []) + dims
    v = [Visual("table", "Detail (all fields)", measures=headline, columns=detail_cols)]
    pages.append(Page("Detailed Data", v, slicers))

    notes = [
        "Use the filters on the left to focus the report (date range, then segment by the dropdowns).",
        "KPI cards show headline totals; charts show trends and breakdowns; tables show the detail.",
        "Move across the page tabs for the summary, trends, segmentation and detail.",
    ]
    return Design(measures=measures, pages=pages, usage_notes=notes,
                  rationale="Deterministic, cardinality-aware design.")
