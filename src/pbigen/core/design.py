"""The design brain: turn a schema + an objective into a logical, story-driven dashboard design.

This module is deterministic and dependency-free. It classifies every column (measure / date /
category / geo / id), proposes a KPI set named after the data's grain, and lays out a narrative:

    Executive Summary -> Trends Over Time -> Drivers & Segments -> Detailed Data -> About

Every page carries a headline question and every visual a subtitle that says how to read it.
Chart choices are driven by the *data shape* (types and distinct-value counts). The LLM
pipeline (:mod:`pbigen.ai.pipeline`) produces the same :class:`Design` structure with far
richer business reasoning; this module is its always-available baseline and fallback.

Author: Arka Gupta
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..ai.knowledge import ENTITY_WORDS, LOWER_IS_BETTER, infer_playbook
from .schema import DATE, DATETIME, NUMERIC_TYPES, Schema, month_column_name

# ---- column-role heuristics -------------------------------------------------
_DATE_HINT = re.compile(r"(date|dttm|_dt$|_ts$|timestamp|period|year_?month|yyyymm|mth|month|year|week|day)", re.I)
_ID_HINT = re.compile(r"(_id$|^id$|_key$|^key$|uuid|guid|_no$|_number$|_code$|ssn|tax_?id|passport|phone|email|account)", re.I)
_CAT_HINT = re.compile(r"(type|status|category|categ|segment|brand|region|area|zone|state|country|city|class|mode|method|group|flag|channel|source|reason|gender|department|company|product|service|tier|band|level)", re.I)
_GEO_HINT = re.compile(r"(lat|lon|lng|postal|zipcode|geohash)", re.I)
# numeric-looking columns that are really codes/geographies/keys — never sum these
_GEOCODE_HINT = re.compile(r"(census|tract|community.?area|\bward\b|district|precinct|\bfips\b|\bblock\b|postal|zip|pincode|geohash|latitude|longitude|\blat\b|\blon\b|\blng\b)", re.I)
_MONEY_HINT = re.compile(r"(income|cost|amount|amt|revenue|sales|price|fee|charge|value|gmv|spend|profit|margin|billing|payment|fare|total|tip|toll|levy)", re.I)
# numeric columns better averaged than summed
_RATE_HINT = re.compile(r"(rate|ratio|pct|percent|avg|average|score|rating|index|per_)", re.I)
# columns that are derived parts of a date — redundant as filters once a real date exists
_PERIOD_PART = re.compile(r"(year|month|week|quarter|day.?of|_dt$|period|_yr$)", re.I)

#: grid spans (of 12 columns) for the layout size hints
SIZES = {"full": 12, "hero": 8, "wide": 8, "half": 6, "third": 4, "side": 4}


@dataclass
class Measure:
    """A logical measure. The emitter turns these into DAX.

    kinds: ``agg`` (SUM/AVERAGE/MIN/MAX/COUNT/DISTINCTCOUNT of a column), ``ratio``
    (SUM(numerator column) / SUM(denominator column)), ``divide`` / ``add`` / ``subtract`` /
    ``multiply`` (KPI op KPI, by name: numerator op denominator), and ``dax`` (a raw expression — generated internally only, never taken from a model)."""

    name: str
    kind: str = "agg"
    column: str | None = None
    agg: str = "SUM"
    numerator: str | None = None
    denominator: str | None = None
    dimension: str | None = None
    money: bool = False
    percent: bool = False
    description: str = ""
    higher_is_better: bool = True
    expression: str | None = None
    hidden: bool = False


@dataclass
class Visual:
    """One visual on a page. Fields not relevant to a type are simply left unset."""

    type: str                    # card|line|area|column|columnStacked|bar|barStacked|combo|
    #                              waterfall|donut|pie|treemap|scatter|table|matrix|slicer
    title: str = ""
    measures: list[str] = field(default_factory=list)
    category: str | None = None
    series: str | None = None
    columns: list[str] = field(default_factory=list)
    x_measure: str | None = None
    y_measure: str | None = None
    size_measure: str | None = None
    line_measures: list[str] = field(default_factory=list)   # combo: the line (Y2) measures
    subtitle: str = ""           # how to read it / the decision it informs
    size: str = ""               # full|hero|wide|half|third|side (layout hint)
    sort_desc: bool = False      # rank categories by the first measure
    labels: bool = False         # show data labels
    delta_label: str | None = None   # card: measure rendering "▲ 4.2% vs prior 30 days"
    delta_color: str | None = None   # card: measure returning the good/bad colour
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
    question: str = ""           # the headline question this page answers
    kind: str = "report"         # report | about
    sections: list[tuple[str, list[str]]] = field(default_factory=list)   # about-page text


@dataclass
class Design:
    measures: list[Measure] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    usage_notes: list[str] = field(default_factory=list)
    rationale: str = ""
    #: the reasoning trail (business context, objectives, KPI tree, research, critique)
    brief: dict = field(default_factory=dict)

    def measure(self, name: str) -> Measure | None:
        return next((m for m in self.measures if m.name == name), None)


# --------------------------------------------------------------------------- classification
def classify(schema: Schema) -> dict[str, list[str]]:
    """Bucket columns into measures / dates / categories / geo / ids.

    A numeric column is only a measure if it is genuinely additive — geographic codes
    (census tract, community area, lat/long), keys and id-like numerics are excluded so they
    are never summed into nonsense measures. Model-calculated columns are skipped.
    """
    out: dict[str, list[str]] = {"measures": [], "dates": [], "categories": [], "geo": [], "ids": []}
    for c in schema.source_columns():
        low = c.name.lower()
        if _GEO_HINT.search(low) or _GEOCODE_HINT.search(low):
            out["geo"].append(c.name)
        elif c.dtype in (DATE, DATETIME) or (_DATE_HINT.search(low) and (c.is_numeric or c.dtype == "string" or c.is_temporal)):
            out["dates"].append(c.name)
        elif _ID_HINT.search(low):
            out["ids"].append(c.name)
        elif c.dtype in NUMERIC_TYPES:
            out["measures"].append(c.name)     # remaining numerics are additive measures
        else:
            out["categories"].append(c.name)
    # categories by cardinality (small = better for donuts/legends), then cat-hint, then length
    out["categories"].sort(key=lambda n: (_card(schema, n), 0 if _CAT_HINT.search(n.lower()) else 1, len(n)))

    def typed(n: str) -> int:
        c = schema.by_name(n)
        return 0 if (c and c.dtype in (DATE, DATETIME)) else 1

    # real typed dates first, then name hints
    out["dates"].sort(key=lambda n: (typed(n), 0 if _DATE_HINT.search(n.lower()) else 1, len(n)))
    return out


def _card(schema: Schema, name: str) -> int:
    c = schema.by_name(name)
    return c.cardinality if (c and c.cardinality is not None) else 10_000


def _pretty(col: str) -> str:
    return col.replace("_", " ").strip().title()


def grain_name(schema: Schema) -> str:
    """Name the row grain after the table: ``taxi_trips`` -> ``Trips``, ``orders`` -> ``Orders``."""
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", schema.table) if t and not t.isdigit()]
    skip = {"db", "fact", "fct", "tbl", "raw", "stg", "vw", "view", "daily", "report", "table", "dim"}
    words = [t for t in tokens if t.lower() not in skip]
    last = (words or tokens or ["records"])[-1]
    if not last.lower().endswith("s") or last.lower().endswith("ss"):
        return "Records"
    return last.title()


def primary_date(schema: Schema) -> str | None:
    """The best real (typed) date column, if any."""
    cls = classify(schema)
    for d in cls["dates"]:
        c = schema.by_name(d)
        if c and c.dtype in (DATE, DATETIME):
            return d
    return None


def trend_axis(schema: Schema, date_col: str | None) -> str | None:
    """Axis for time trends: the monthly grain when the model has it, else the date itself."""
    if not date_col:
        return None
    month = month_column_name(date_col)
    return month if schema.by_name(month) else date_col


def _entity_id(schema: Schema) -> str | None:
    cls = classify(schema)
    for col in cls["ids"]:
        low = col.lower()
        if any(w in low for w in ENTITY_WORDS):
            return col
    return None


def propose_measures(schema: Schema, limit: int = 5) -> list[Measure]:
    """Synthesise a KPI set: volume (named after the grain), distinct entities, totals, averages
    and an efficiency ratio (lead money measure per record)."""
    cls = classify(schema)
    grain = grain_name(schema)
    unit = grain[:-1].lower() if grain.endswith("s") else "record"
    out: list[Measure] = [Measure(grain, "agg", column=None, agg="COUNT",
                                  description=f"Number of rows (one row = one {unit}).")]
    entity = _entity_id(schema)
    money_total: str | None = None
    for col in cls["measures"][:limit]:
        low = col.lower()
        hib = not bool(LOWER_IS_BETTER.search(low))
        if _RATE_HINT.search(low):
            out.append(Measure("Avg " + _pretty(col), "agg", column=col, agg="AVERAGE",
                               percent=bool(re.search(r"(rate|ratio|pct|percent)", low)),
                               description=f"Average of {col} per row.", higher_is_better=hib))
        else:
            m = Measure("Total " + _pretty(col), "agg", column=col, agg="SUM",
                        money=bool(_MONEY_HINT.search(low)), description=f"Sum of {col}.",
                        higher_is_better=hib)
            out.append(m)
            if m.money and money_total is None:
                money_total = m.name
    if entity:
        noun = _pretty(re.sub(r"(_id|_key|_no|_number|id)$", "", entity, flags=re.I)) or "Entitie"
        out.insert(1, Measure(f"Unique {noun}s" if not noun.endswith("s") else f"Unique {noun}",
                              "agg", column=entity, agg="DISTINCTCOUNT",
                              description=f"Distinct count of {entity}."))
    if money_total:
        base = money_total.replace("Total ", "")
        out.append(Measure(f"Avg {base} per {unit.title()}", "divide",
                           numerator=money_total, denominator=grain, money=True,
                           description=f"{money_total} ÷ {grain}."))
    return out


def _good_slicer(name: str, schema: Schema, real_dates: set[str]) -> bool:
    if name in real_dates:
        return True
    if real_dates and _PERIOD_PART.search(name):          # redundant with the date range
        return False
    col = schema.by_name(name)
    card = col.cardinality if col else None
    return card is None or card <= 50                     # dropdowns only for low-cardinality


# --------------------------------------------------------------------------- deterministic story
def design(schema: Schema, objective: str = "", measures: list[Measure] | None = None,
           context: str = "") -> Design:
    """Deterministic, cardinality-aware, story-structured dashboard design."""
    cls = classify(schema)
    playbook = infer_playbook(schema.names(), f"{objective} {context} {schema.table}")
    real_dates = {c.name for c in schema.source_columns() if c.dtype in (DATE, DATETIME)}
    measures = measures or propose_measures(schema)
    names = [m.name for m in measures]
    headline = names[:5] or ["(no measure)"]
    lead = headline[0]
    # the money / value measure is the most interesting lead when present
    value = next((m.name for m in measures if m.money and m.kind == "agg"), None)
    efficiency = next((m.name for m in measures if m.kind == "divide"), None) or \
        next((m.name for m in measures if m.agg == "AVERAGE" and m.column), None)
    story_lead = value or lead

    date = primary_date(schema) or (cls["dates"][0] if cls["dates"] else None)
    axis = trend_axis(schema, date) if date in real_dates else date
    dims = [d for d in cls["categories"] if _card(schema, d) <= 50][:4]
    dim0 = dims[0] if dims else None
    dim1 = dims[1] if len(dims) > 1 else None
    dim2 = dims[2] if len(dims) > 2 else None

    def low_card(col: str | None, n: int = 6) -> bool:
        return bool(col) and _card(schema, col) <= n

    series1 = next((d for d in dims if low_card(d, 6)), None)

    def breakdown(metric: str, dim: str, size: str = "side") -> Visual:
        if low_card(dim):
            return Visual("donut", f"{metric} share by {_pretty(dim)}", measures=[metric], category=dim,
                          subtitle=f"Which {_pretty(dim).lower()} contributes most — slices sum to 100%.",
                          size=size, labels=True)
        return Visual("bar", f"{metric} by {_pretty(dim)}", measures=[metric], category=dim, sort_desc=True,
                      subtitle=f"Ranked high to low — the top {_pretty(dim).lower()} values drive the total.",
                      size=size, labels=True)

    slicers = [s for s in ([date] if date else []) + dims if _good_slicer(s, schema, real_dates)][:5]
    pages: list[Page] = []

    # 1) Executive Summary — KPI row with period deltas, hero trend, main driver, rankings
    v = [Visual("card", m, measures=[m]) for m in headline[:4]]
    if axis:
        if value and value != lead:
            v.append(Visual("combo", f"{lead} and {value} by month", measures=[lead], line_measures=[value],
                            category=axis, size="hero",
                            subtitle="Columns = volume, line = value. Diverging lines signal a price or mix shift."))
        else:
            v.append(Visual("line", f"{story_lead} by month", measures=[story_lead], category=axis, size="hero",
                            subtitle="Month-by-month trend — look for seasonality, step changes and inflections."))
    if dim0:
        v.append(breakdown(story_lead, dim0, "side" if axis else "half"))
    if dim1:
        v.append(Visual("bar", f"Top {_pretty(dim1)} by {story_lead}", measures=[story_lead], category=dim1,
                        sort_desc=True, labels=True, size="half",
                        subtitle=f"Where to focus: the {_pretty(dim1).lower()} values that matter most."))
    if efficiency and dim0:
        v.append(Visual("column", f"{efficiency} by {_pretty(dim0)}", measures=[efficiency], category=dim0,
                        sort_desc=True, labels=True, size="half",
                        subtitle="Efficiency, not just volume — which segments earn more per unit."))
    pages.append(Page("Executive Summary", v, slicers,
                      question=f"How are we performing on {story_lead.lower()}, and what is driving it?"))

    # 2) Trends Over Time — trends of the key measures and mix over time
    if axis:
        v = [Visual("line", f"{lead} trend", measures=[lead], category=axis, size="half",
                    subtitle=f"Monthly {lead.lower()} — the volume pulse of the business.")]
        second = value if value and value != lead else (headline[1] if len(headline) > 1 else None)
        if second:
            v.append(Visual("area", f"{second} trend", measures=[second], category=axis, size="half",
                            subtitle=f"Monthly {second.lower()} — compare its shape with volume."))
        if series1:
            v.append(Visual("columnStacked", f"{lead} mix by {_pretty(series1)} over time", measures=[lead],
                            category=axis, series=series1, size="full",
                            subtitle=f"How the {_pretty(series1).lower()} mix shifts month to month."))
        if efficiency:
            v.append(Visual("line", f"{efficiency} trend", measures=[efficiency], category=axis, size="full",
                            subtitle="Unit economics over time — rising volume with falling value is a warning sign."))
        pages.append(Page("Trends Over Time", v, slicers,
                          question="How is performance changing month to month — is it volume or value?"))

    # 3) Drivers & Segments — rank each dimension, composition, two-way breakdown, relationships
    if dim0:
        v = []
        for d in [x for x in (dim0, dim1, dim2) if x]:
            v.append(Visual("bar", f"{story_lead} by {_pretty(d)}", measures=[story_lead], category=d,
                            sort_desc=True, labels=True, size="third",
                            subtitle=f"Ranked {_pretty(d).lower()} — compare the leaders with the tail."))
        big = next((d for d in dims if not low_card(d, 6)), None)
        if big:
            v.append(Visual("treemap", f"{story_lead} composition by {_pretty(big)}", measures=[story_lead],
                            category=big, size="half",
                            subtitle="Area = contribution. Many small tiles means a long tail."))
        mx_measures = [n for n in headline[:4] if n != "(no measure)"]
        v.append(Visual("matrix", f"{_pretty(dim0)} scorecard", measures=mx_measures, category=dim0,
                        series=series1 if series1 and series1 != dim0 else None, size="half",
                        subtitle="Exact values for every segment — the numbers behind the charts."))
        if efficiency and dim1 and value:
            v.append(Visual("scatter", f"Volume vs value by {_pretty(dim1)}", measures=[lead, efficiency],
                            x_measure=lead, y_measure=efficiency, category=dim1, size="half",
                            subtitle="Top-right = high volume and high value; bottom-right = volume at low value."))
        pages.append(Page("Drivers & Segments", v, slicers,
                          question=f"Which segments drive {story_lead.lower()}, and where are the gaps?"))

    # 4) Detailed Data — a focused table (a few dims + headline measures, not every field)
    detail_cols = ([date] if date else []) + dims[:3]
    v = [Visual("table", "Detail", measures=headline[:4], columns=detail_cols, size="full",
                subtitle="Row-level figures for verification and export. Use the filters to narrow down.")]
    pages.append(Page("Detailed Data", v, slicers, question="What are the underlying numbers?"))

    notes = [
        "Use the filters to focus the report (date range first, then the dropdowns).",
        "KPI cards show the total for the selection plus the last 30 days vs the prior 30.",
        "Pages flow summary -> trends -> drivers -> detail; the last page defines every KPI.",
    ]
    grain = grain_name(schema)
    brief = {
        "engine": "deterministic",
        "domain": playbook.name,
        "north_star": playbook.north_star,
        "objective": objective or f"Monitor {playbook.north_star.lower()} and what drives it",
        "objectives": list(playbook.objectives),
        "audience": "Business leaders and analysts",
        "grain": f"One row per {grain[:-1].lower() if grain.endswith('s') else 'record'}",
        "kpis": [{"name": m.name, "definition": m.description or m.name,
                  "unit": "money" if m.money else ("percent" if m.percent else
                                                   "count" if m.agg in ("COUNT", "DISTINCTCOUNT") else "number"),
                  "higher_is_better": m.higher_is_better} for m in measures],
        "storyline": [{"page": p.name, "question": p.question} for p in pages],
    }
    return Design(measures=measures, pages=pages, usage_notes=notes,
                  rationale="Deterministic, cardinality-aware, story-structured design.", brief=brief)


# --------------------------------------------------------------------------- shared finishing
def add_comparisons(design: Design, schema: Schema, days: int = 30) -> Design:
    """Give every KPI card a period-over-period delta (last ``days`` vs the prior ``days``).

    Adds three measures per carded KPI: ``<M> vs Prior %`` (visible), and hidden label/colour
    helpers the card subtitle binds to. Colour respects the KPI's direction (cost up = red).
    Needs a typed date column; otherwise cards are left as they are."""
    date = primary_date(schema)
    if not date:
        return design
    t, d = schema.table, date
    have = {m.name for m in design.measures}
    for page in design.pages:
        for v in page.visuals:
            if v.type not in ("card", "kpi") or not v.measures:
                continue
            base = design.measure(v.measures[0])
            if base is None or base.kind == "dax":
                continue
            pct, label, color = f"{base.name} vs Prior %", f"{base.name} Trend Label", f"{base.name} Trend Colour"
            if pct not in have:
                design.measures.append(Measure(
                    pct, "dax", percent=True, higher_is_better=base.higher_is_better,
                    description=f"Change in {base.name}: last {days} days vs the prior {days} days "
                                "(relative to the latest date in the selection).",
                    expression=(
                        f"VAR _end = CALCULATE(MAX('{t}'[{d}]), ALLSELECTED('{t}')) "
                        f"VAR _cur = CALCULATE([{base.name}], '{t}'[{d}] > _end - {days}, '{t}'[{d}] <= _end) "
                        f"VAR _prev = CALCULATE([{base.name}], '{t}'[{d}] > _end - {2 * days}, '{t}'[{d}] <= _end - {days}) "
                        "RETURN DIVIDE(_cur - _prev, _prev)"
                    )))
                good, bad = ("#12B76A", "#F04438") if base.higher_is_better else ("#F04438", "#12B76A")
                design.measures.append(Measure(
                    label, "dax", hidden=True,
                    expression=(
                        f"VAR _d = [{pct}] RETURN IF(ISBLANK(_d), \"No prior-period data\", "
                        f"IF(_d >= 0, \"▲ \", \"▼ \") & FORMAT(ABS(_d), \"0.0%\") & \" vs prior {days} days\")"
                    )))
                design.measures.append(Measure(
                    color, "dax", hidden=True,
                    expression=f"VAR _d = [{pct}] RETURN IF(ISBLANK(_d), \"#667085\", IF(_d >= 0, \"{good}\", \"{bad}\"))"))
                have |= {pct, label, color}
            v.delta_label, v.delta_color = label, color
    return design


def add_about_page(design: Design, schema: Schema, source_label: str = "") -> Design:
    """Append the "About this report" page: purpose, objectives, story, KPI definitions, data."""
    if any(p.kind == "about" for p in design.pages):
        return design
    b = design.brief or {}
    sections: list[tuple[str, list[str]]] = []
    purpose = [str(b.get("objective") or "Monitor performance and its drivers.")]
    if b.get("north_star"):
        ns = b["north_star"]
        purpose.append(f"North-star metric: {ns.get('name', ns) if isinstance(ns, dict) else ns}.")
    if b.get("audience"):
        aud = b["audience"]
        if isinstance(aud, list):
            aud = ", ".join(a.get("role", str(a)) if isinstance(a, dict) else str(a) for a in aud)
        purpose.append(f"Audience: {aud}.")
    sections.append(("Purpose", purpose))
    objs = [str(o.get("objective", o)) if isinstance(o, dict) else str(o) for o in (b.get("objectives") or [])]
    if objs:
        sections.append(("Objectives this report answers", objs[:6]))
    story = [f"{p.name}: {p.question}" for p in design.pages if p.kind == "report" and p.question]
    if story:
        sections.append(("How the story flows", story[:7]))
    kpis = []
    for m in design.measures:
        if m.hidden:
            continue
        arrow = "higher is better" if m.higher_is_better else "lower is better"
        kpis.append(f"{m.name} — {m.description or m.name} ({arrow})")
    sections.append(("KPI definitions", kpis[:14]))
    sections.append(("How to use", list(design.usage_notes[:4])))
    data = [f"Source: {source_label or schema.table}."]
    if b.get("grain"):
        data.append(f"Grain: {b['grain']}.")
    for c in (b.get("caveats") or [])[:3]:
        data.append(f"Caveat: {c}")
    for g in (b.get("gaps") or [])[:2]:
        data.append(f"Not answerable from this data: {g}")
    sections.append(("Data", data))
    design.pages.append(Page("About this report", [], [], question="What does this report measure, and how?",
                             kind="about", sections=sections))
    return design


__all__ = ["Measure", "Visual", "Page", "Design", "SIZES", "classify", "propose_measures", "design",
           "add_comparisons", "add_about_page", "primary_date", "trend_axis", "grain_name"]
