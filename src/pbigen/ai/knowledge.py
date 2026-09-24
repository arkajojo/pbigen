"""Curated dashboard-design knowledge: storytelling, chart grammar, KPI craft and domain playbooks.

This is the "built-in research" the design pipeline grounds itself in. It is deliberately
plain text + small dicts (no dependencies) so that:

* the deterministic designer can infer a domain and its storyline offline, and
* every LLM stage receives the same distilled, opinionated guidance — the difference between a
  generic "X by Y" chart dump and a structured executive story.

Sources distilled here are public, well-established practice: IBCS (SUCCESS rules), Stephen Few
(information dashboard design), Cole Nussbaumer Knaflic (storytelling with data), Barbara Minto
(pyramid principle), and the standard KPI trees used across each industry.

Author: Arka Gupta
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- principles
STORY_PRINCIPLES = """\
STORYTELLING (Minto pyramid + Knaflic):
- Lead with the answer. Page 1 answers "how are we doing?" in 5 seconds: the north-star KPI and
  3-5 supporting KPIs, each WITH context (vs prior period / target / benchmark), then the one
  trend that matters most and the biggest driver of change.
- Then go down the pyramid, one question per page: situation (what happened) -> drivers
  (why it happened: which segments / channels / products moved) -> diagnosis (where exactly:
  mix, efficiency, outliers, funnel leaks) -> detail (the rows, for self-serve verification).
- Every page carries a headline QUESTION (what it answers) and every visual a SUBTITLE that
  says how to read it or what decision it informs. Titles are specific, never "Chart 1".
- Close with an "About this report" page: purpose, audience, KPI definitions (formula + unit +
  direction), data source/grain/refresh, known caveats. A dashboard nobody trusts is not used.
- Cover everything that matters, nothing that does not: each objective must be answered by at
  least one visual; each visual must serve an objective. Remove decoration and redundancy.
"""

VISUAL_GRAMMAR = """\
CHART GRAMMAR (Few + IBCS):
- Trend over time -> line (<=3 series) or area (cumulative / composition over time). Use a
  monthly (or weekly) grain, never raw timestamps. Two measures with different units -> combo
  (columns for volume + line for rate/value).
- Ranking / comparison across categories -> horizontal bar sorted descending (readable labels).
  Few (<=8) ordered periods -> column.
- Part-to-whole -> donut ONLY for <=6 slices; otherwise a sorted bar or a treemap (many parts).
- Contribution / bridge (start -> changes -> end, or a total decomposed) -> waterfall.
- Relationship between two measures across entities -> scatter (optionally sized by a third).
- Two-dimensional breakdown / exact values -> matrix (rows x low-cardinality columns).
- Row-level detail for verification -> table with a handful of meaningful columns.
- Headline numbers -> KPI cards with period-over-period change coloured by whether the change
  is good or bad (direction depends on the KPI: cost/cancellations/churn up is BAD).
- Cardinality rules: a legend/series field must have <=6 values; a dropdown slicer <=50
  values; dates are range (between) slicers; never chart an id or a free-text column; never
  sum codes (zip, tract, lat/long, ids).
- Density: 4-9 visuals per page. KPI row on top, one hero visual, supporting visuals below,
  detail last. Consistent measure names and units across pages. No 3D, no gauges without a
  target, no pies of many slices, no dual axes with unrelated units.
"""

KPI_CRAFT = """\
KPI CRAFT:
- Build a KPI tree: one north-star outcome, decomposed into drivers (volume x rate x value)
  e.g. Revenue = Orders x Avg Order Value; Orders = Visitors x Conversion.
- Each KPI needs: a precise definition, unit (money / percent / count / number), the direction
  that is good (higher_is_better), and why it matters for a decision.
- Prefer ratios and averages that normalise volume (per trip, per customer, conversion %) next
  to absolute totals; totals alone hide efficiency.
- Distinct counts of the business entity (customers, drivers, users, accounts) are usually a
  top-3 KPI. Record counts are a fallback, not an insight — name them after the grain
  (e.g. "Trips", "Orders", "Bookings").
"""

ANTI_PATTERNS = """\
ANTI-PATTERNS TO REJECT:
- "Everything by everything": a chart per column with no question behind it.
- Generic titles ("Sum of amount by type"); unlabeled units; unexplained acronyms.
- KPI cards without comparison; trends on raw timestamps; donuts with 20 slices.
- Legends with hundreds of values; slicers on ids; averaging averages; summing rates.
- Repeating the same visual on several pages; detail tables with 30 columns.
- Pages without a question; a story that never reaches "why" or "so what".
"""


# --------------------------------------------------------------------------- domain playbooks
@dataclass(frozen=True)
class Playbook:
    key: str
    name: str
    keywords: tuple[str, ...]
    north_star: str
    objectives: tuple[str, ...]
    kpis: tuple[str, ...]
    storyline: tuple[str, ...]
    pitfalls: tuple[str, ...] = field(default_factory=tuple)

    def as_text(self) -> str:
        lines = [f"DOMAIN PLAYBOOK — {self.name}",
                 f"North star: {self.north_star}",
                 "Objectives: " + "; ".join(self.objectives),
                 "Standard KPIs: " + "; ".join(self.kpis),
                 "Proven storyline: " + " -> ".join(self.storyline)]
        if self.pitfalls:
            lines.append("Pitfalls: " + "; ".join(self.pitfalls))
        return "\n".join(lines)


PLAYBOOKS: tuple[Playbook, ...] = (
    Playbook(
        "mobility", "Mobility, ride-hailing, taxi & transport",
        ("trip", "ride", "booking", "driver", "taxi", "fare", "pickup", "dropoff", "vehicle",
         "fleet", "passenger", "journey", "route", "mileage", "miles", "km", "cab", "rider"),
        "Completed trips (and the revenue they generate)",
        ("Grow completed trips and revenue", "Balance supply (drivers/vehicles) with demand",
         "Improve fulfilment and reduce cancellations", "Raise revenue per trip and per driver"),
        ("Completed trips", "Gross booking value / fare revenue", "Avg fare per trip",
         "Active drivers / vehicles", "Trips per driver", "Fulfilment / completion rate",
         "Cancellation rate (lower is better)", "Avg trip distance / duration", "Tips & tolls share"),
        ("Performance at a glance", "Demand over time (seasonality, peak hours, day-of-week)",
         "Where & what (zones, payment types, products)", "Supply & efficiency (per driver/vehicle)",
         "Trip detail"),
        ("Summing geo codes/coordinates", "Mixing booked vs completed trips",
         "Averages skewed by outlier fares/distances"),
    ),
    Playbook(
        "commerce", "Sales, retail & e-commerce",
        ("order", "sales", "revenue", "product", "sku", "customer", "cart", "store", "invoice",
         "discount", "quantity", "basket", "checkout", "merchant", "retail", "item"),
        "Net revenue",
        ("Grow revenue and margin", "Grow and retain customers", "Optimise product & channel mix",
         "Protect margin from discounts and returns"),
        ("Net revenue", "Orders", "Average order value", "Units sold", "Unique customers",
         "Revenue per customer", "Gross margin %", "Discount rate", "Return rate (lower is better)"),
        ("Performance at a glance", "Revenue trend & seasonality", "Mix: products, categories, channels, regions",
         "Customers: new vs returning, value distribution", "Order detail"),
        ("Revenue without returns/discounts", "Counting line items as orders"),
    ),
    Playbook(
        "marketing", "Marketing, acquisition & growth",
        ("campaign", "impression", "click", "ctr", "cpc", "cpm", "spend", "conversion", "lead",
         "channel", "utm", "ad", "adset", "creative", "install", "acquisition", "attribution"),
        "Conversions (or revenue) at an efficient cost",
        ("Maximise conversions within budget", "Allocate spend to the best channels/campaigns",
         "Improve funnel conversion", "Lower acquisition cost"),
        ("Spend", "Impressions", "Clicks", "CTR", "Conversions", "Conversion rate",
         "Cost per acquisition (lower is better)", "ROAS", "CPC / CPM (lower is better)"),
        ("Performance at a glance", "Spend & results over time", "Channel & campaign efficiency",
         "Funnel diagnosis", "Campaign detail"),
        ("Summing rates (CTR, CVR)", "Comparing channels on volume without efficiency"),
    ),
    Playbook(
        "product", "Digital product, app & engagement analytics",
        ("user", "session", "event", "app", "launch", "screen", "page_view", "pageview", "device",
         "platform", "os", "version", "retention", "active", "dau", "mau", "signup", "login", "feature"),
        "Active users engaging with the core value",
        ("Grow active users", "Deepen engagement", "Improve retention", "Spot platform/version issues"),
        ("Daily/monthly active users", "Sessions", "Sessions per user", "New users / sign-ups",
         "Retention / returning users", "Events per session", "Crash or error rate (lower is better)"),
        ("Engagement at a glance", "Usage trends (daily/weekly patterns)", "Segments: platform, version, country, channel",
         "Behaviour & feature adoption", "Event detail"),
        ("Counting events as users", "Mixing app versions without a platform split"),
    ),
    Playbook(
        "finance", "Finance, P&L & cost management",
        ("cost", "expense", "budget", "actual", "forecast", "ledger", "gl", "account", "profit",
         "margin", "ebitda", "opex", "capex", "cost_center", "costcenter", "variance", "income"),
        "Profit vs plan",
        ("Deliver profit vs budget", "Control costs by cost centre", "Explain variances", "Forecast accurately"),
        ("Revenue", "Costs (lower is better)", "Gross / net margin %", "Actual vs budget variance",
         "Variance %", "Cost per unit", "Forecast accuracy"),
        ("Financial position at a glance", "Actual vs budget over time", "Variance bridge (waterfall)",
         "Cost-centre / account drill-down", "Ledger detail"),
        ("Sign conventions (costs negative vs positive)", "Comparing periods of different lengths"),
    ),
    Playbook(
        "operations", "Operations, logistics & supply chain",
        ("shipment", "delivery", "warehouse", "inventory", "stock", "sla", "lead_time", "supplier",
         "carrier", "dispatch", "fulfilment", "fulfillment", "backlog", "throughput", "late", "ontime"),
        "On-time, in-full delivery at the lowest cost",
        ("Deliver on time and in full", "Increase throughput", "Reduce cost and waste", "Manage inventory health"),
        ("On-time delivery %", "Throughput / volume", "Avg lead time (lower is better)", "Backlog",
         "Cost per shipment (lower is better)", "Stock-outs (lower is better)", "Inventory turns"),
        ("Service level at a glance", "Volume & SLA trend", "By site, carrier, supplier", "Bottlenecks & exceptions",
         "Shipment detail"),
        ("Averaging lead times with outliers", "Mixing units of measure"),
    ),
    Playbook(
        "service", "Customer service, support & feedback",
        ("ticket", "case", "complaint", "feedback", "rating", "survey", "nps", "csat", "agent",
         "resolution", "response", "sentiment", "review", "star", "remark", "escalation"),
        "Customer satisfaction with fast resolution",
        ("Raise satisfaction", "Resolve faster", "Reduce contact volume at the root", "Balance agent workload"),
        ("Tickets / feedback volume", "CSAT / avg rating", "NPS", "First response time (lower is better)",
         "Resolution time (lower is better)", "Resolution rate", "Top complaint reasons"),
        ("Satisfaction at a glance", "Volume & satisfaction over time", "Drivers: reasons, channels, products",
         "Team & SLA performance", "Ticket / feedback detail"),
        ("Averaging ratings without response counts", "Free-text fields as chart categories"),
    ),
    Playbook(
        "people", "HR & people analytics",
        ("employee", "headcount", "hire", "attrition", "salary", "department", "tenure", "grade",
         "leave", "absence", "overtime", "recruit", "candidate", "payroll"),
        "Healthy, engaged, retained workforce",
        ("Plan headcount", "Reduce regretted attrition", "Fair and efficient compensation", "Improve hiring"),
        ("Headcount", "Hires", "Attrition rate (lower is better)", "Avg tenure", "Time to hire (lower is better)",
         "Payroll cost", "Absence rate (lower is better)"),
        ("Workforce at a glance", "Headcount & attrition trend", "By department, grade, location",
         "Compensation & equity", "Employee detail"),
        ("Exposing personal data", "Small-group percentages"),
    ),
    Playbook(
        "subscription", "SaaS & subscription",
        ("subscription", "plan", "mrr", "arr", "churn", "renewal", "trial", "seat", "tenant",
         "license", "billing", "invoice", "upgrade", "downgrade", "account"),
        "Net recurring revenue growth",
        ("Grow MRR/ARR", "Reduce churn", "Expand existing accounts", "Convert trials"),
        ("MRR / ARR", "New MRR", "Churned MRR (lower is better)", "Net revenue retention", "Active accounts",
         "ARPA", "Trial conversion %", "Logo churn rate (lower is better)"),
        ("Recurring revenue at a glance", "MRR movement (new, expansion, churn) — waterfall",
         "By plan, segment, region", "Cohorts & retention", "Account detail"),
        ("Mixing bookings and recognised revenue",),
    ),
    Playbook(
        "health", "Healthcare & clinical operations",
        ("patient", "admission", "discharge", "diagnosis", "clinic", "hospital", "bed", "claim",
         "provider", "encounter", "procedure", "readmission", "appointment"),
        "Quality outcomes delivered efficiently",
        ("Improve outcomes", "Improve access and throughput", "Control cost per case"),
        ("Encounters / admissions", "Avg length of stay (lower is better)", "Readmission rate (lower is better)",
         "Bed occupancy", "No-show rate (lower is better)", "Cost per case"),
        ("Operations at a glance", "Volume & capacity over time", "By department, provider, diagnosis",
         "Quality & outcomes", "Encounter detail"),
        ("Exposing patient-level data",),
    ),
)

GENERIC = Playbook(
    "general", "General business performance",
    (),
    "The primary outcome measure of this data",
    ("Understand overall performance", "See how it changes over time", "Find the segments that drive it",
     "Enable self-serve detail"),
    ("Volume (records named after the grain)", "Primary totals", "Averages per record",
     "Distinct entities", "Share by top segment"),
    ("Performance at a glance", "Trends over time", "Drivers & segments", "Detail"),
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


def infer_playbook(column_names: list[str], extra_text: str = "") -> Playbook:
    """Pick the playbook whose vocabulary best matches the columns + any user-provided context."""
    toks = set()
    for name in column_names:
        toks |= _tokens(name)
        toks.add(name.lower())
    toks |= _tokens(extra_text)
    best, score = GENERIC, 0
    for pb in PLAYBOOKS:
        s = sum(1 for k in pb.keywords if k in toks or any(k in t for t in toks if len(k) > 3))
        if s > score:
            best, score = pb, s
    return best if score >= 2 else GENERIC


def playbook_by_key(key: str) -> Playbook:
    return next((p for p in PLAYBOOKS if p.key == key), GENERIC)


def design_handbook() -> str:
    """All general principles in one block, for prompts."""
    return "\n".join([STORY_PRINCIPLES, VISUAL_GRAMMAR, KPI_CRAFT, ANTI_PATTERNS])


# entity words: a distinct count of one of these is a headline KPI ("Unique Customers")
ENTITY_WORDS = ("customer", "user", "driver", "vehicle", "passenger", "rider", "account", "member",
                "patient", "employee", "merchant", "store", "agent", "device", "subscriber", "client",
                "taxi", "company", "supplier")

# measures where an increase is bad — used to colour period-over-period deltas
LOWER_IS_BETTER = re.compile(
    r"(cost|expense|cancel|churn|complaint|defect|error|crash|fail|late|delay|lead.?time|"
    r"duration|wait|refund|return|discount|attrition|absence|no.?show|readmission|bounce|cpa|cpc|cpm)",
    re.I,
)

__all__ = ["Playbook", "PLAYBOOKS", "GENERIC", "infer_playbook", "playbook_by_key",
           "design_handbook", "STORY_PRINCIPLES", "VISUAL_GRAMMAR", "KPI_CRAFT", "ANTI_PATTERNS",
           "ENTITY_WORDS", "LOWER_IS_BETTER"]
