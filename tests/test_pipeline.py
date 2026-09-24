"""The staged AI pipeline, driven by a scripted fake model (no network, no key).

Author: Arka Gupta
"""
from __future__ import annotations

import json

import pytest

import pbigen
from pbigen.ai.knowledge import infer_playbook
from pbigen.ai.pipeline import DesignPipeline, DesignRequest, parse_design
from pbigen.core.design import add_about_page, add_comparisons, design
from pbigen.core.schema import Column, Schema, with_time_grain
from pbigen.emit.model import table_tmdl
from pbigen.models.base import Model


def _schema() -> Schema:
    s = Schema("trips", [
        Column("trip_start", "datetime"), Column("payment_type", "string", cardinality=5),
        Column("company", "string", cardinality=40), Column("taxi_id", "string", cardinality=900),
        Column("fare", "float"), Column("tips", "float"), Column("trip_miles", "float"),
    ])
    return with_time_grain(s, "trip_start")


STORY = {
    "measures": [
        {"name": "Trips", "kind": "agg", "agg": "COUNT", "column": None, "unit": "count"},
        {"name": "Fare Revenue", "kind": "agg", "agg": "SUM", "column": "fare", "unit": "money"},
        {"name": "Tips", "kind": "agg", "agg": "SUM", "column": "tips", "unit": "money"},
        {"name": "Gross Revenue", "kind": "add", "numerator": "Fare Revenue", "denominator": "Tips", "unit": "money"},
        {"name": "Avg Fare per Trip", "kind": "divide", "numerator": "Fare Revenue", "denominator": "Trips"},
        {"name": "Bogus", "kind": "agg", "agg": "SUM", "column": "not_a_column"},
        {"name": "Active Taxis", "kind": "agg", "agg": "DISTINCTCOUNT", "column": "taxi_id"},
    ],
    "pages": [
        {"name": "Performance", "question": "How are we doing?", "slicers": ["trip_start", "taxi_id", "company"],
         "visuals": [
             {"type": "card", "title": "Trips", "measures": ["Trips"]},
             {"type": "card", "title": "Gross", "measures": ["Gross Revenue"]},
             {"type": "combo", "title": "Volume vs value", "subtitle": "read me", "category": "trip_start",
              "measures": ["Trips"], "line_measures": ["Avg Fare per Trip"], "size": "hero"},
             {"type": "donut", "title": "Too many slices", "category": "company", "measures": ["Trips"]},
             {"type": "bar", "title": "Broken", "category": "nope", "measures": ["Trips"]},
             {"type": "treemap", "title": "Mix", "category": "company", "series": "payment_type",
              "measures": ["Fare Revenue"]},
         ]},
        {"name": "About", "visuals": [{"type": "card", "measures": ["Trips"]}]},
    ],
    "usage_notes": ["Use the date range first."],
}


class _Scripted:
    """Answers each stage from a script, recording the prompts it saw."""

    def __init__(self, fail_web: bool = False):
        self.calls: list[tuple[str, str, bool]] = []
        self.fail_web = fail_web

    def __call__(self, system: str, user: str, web: bool = False) -> str:
        self.calls.append((system, user, web))
        if web and self.fail_web:
            raise RuntimeError("no web search")
        if "principal analytics consultant" in system:
            return json.dumps({"domain": "Taxi mobility", "grain": "one row = one trip",
                               "audience": [{"role": "COO", "decisions": ["fleet sizing"]}],
                               "caveats": ["fares exclude surcharges"]})
        if "head of strategy" in system:
            return json.dumps({"north_star": {"name": "Completed trips"},
                               "objectives": [{"objective": "Grow trips", "decisions": ["pricing"]}],
                               "kpis": [{"name": "Trips"}], "gaps": ["No cancellation data"]})
        if "research analyst" in system:
            return "```json\n" + json.dumps({"findings": [{"insight": "Lead with trips"}],
                                             "sources": ["https://a", "https://a", "https://b"]}) + "\n```"
        if "reviewer" in system:
            return json.dumps({"issues": [{"issue": "x", "fix": "y"}], "design": STORY})
        return json.dumps(STORY)


def test_pipeline_runs_all_stages_and_validates():
    fake = _Scripted()
    d = DesignPipeline(fake, "fake", verbose=False).run(_schema(), DesignRequest(objective="grow", research="web"))
    assert len(fake.calls) == 5 and fake.calls[2][2] is True           # research used web search
    names = {m.name for m in d.measures}
    assert {"Trips", "Gross Revenue", "Avg Fare per Trip", "Active Taxis"} <= names
    assert "Bogus" not in names                                          # unknown column dropped
    page = d.pages[0]
    assert [p.name for p in d.pages] == ["Performance"]                  # model "About" page ignored
    combo = next(v for v in page.visuals if v.type == "combo")
    assert combo.category == "trip_start Month" and combo.line_measures == ["Avg Fare per Trip"]
    assert next(v for v in page.visuals if v.title == "Too many slices").type == "bar"   # 40 > 6 slices
    assert not any(v.title == "Broken" for v in page.visuals)
    tm = next(v for v in page.visuals if v.type == "treemap")
    assert tm.series == "payment_type"
    assert "taxi_id" not in page.slicers                                 # 900 values -> not a dropdown
    b = d.brief
    assert b["domain"] == "Taxi mobility" and b["north_star"] == "Completed trips"
    assert b["gaps"] == ["No cancellation data"] and b["critique"]
    assert [s["status"] for s in b["stages"]] == ["ok"] * 5


def test_pipeline_web_failure_falls_back_to_builtin_research():
    fake = _Scripted(fail_web=True)
    d = DesignPipeline(fake, "fake", verbose=False).run(_schema(), DesignRequest(research="web"))
    assert "built-in" in d.brief["research"]["mode"]


def test_pipeline_garbage_falls_back_to_deterministic():
    d = DesignPipeline(lambda s, u, web=False: "not json at all", "fake", verbose=False).run(
        _schema(), DesignRequest())
    assert d.rationale.startswith("deterministic") and d.pages


def test_arithmetic_kpis_emit_dax():
    d = parse_design(STORY, _schema(), design(_schema()))
    tmdl = table_tmdl(_schema(), d.measures, "let Source = 1 in Source")
    assert "measure 'Gross Revenue' = [Fare Revenue] + [Tips]" in tmdl
    assert "measure 'Avg Fare per Trip' = DIVIDE([Fare Revenue], [Trips])" in tmdl
    assert "column 'trip_start Month' = DATE(YEAR('trips'[trip_start]), MONTH('trips'[trip_start]), 1)" in tmdl


def test_cards_get_directional_deltas_and_about_page():
    s = Schema("orders", [Column("order_date", "date"), Column("region", "string", cardinality=4),
                          Column("revenue", "float"), Column("cost", "float")])
    d = design(s)
    d = add_comparisons(d, s, days=30)
    card = next(v for v in d.pages[0].visuals if v.type == "card")
    assert card.delta_label and card.delta_color
    cost_col = d.measure("Total Cost Trend Colour")
    if cost_col:                                   # cost up is bad -> red first branch
        assert '"#F04438", "#12B76A"' in cost_col.expression
    d = add_about_page(d, s)
    about = d.pages[-1]
    assert about.kind == "about" and any(h == "KPI definitions" for h, _ in about.sections)


def test_playbook_inference():
    assert infer_playbook(["trip_start", "fare", "taxi_id", "pickup_area"]).key == "mobility"
    assert infer_playbook(["order_id", "revenue", "sku", "customer_id"]).key == "commerce"
    assert infer_playbook(["a", "b"]).key == "general"


def test_generate_with_a_custom_model_writes_design_md(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")

    class Fixed(Model):
        name = "fixed"

        def design(self, schema, objective, request=None):
            return DesignPipeline(_Scripted(), "fixed", verbose=False).run(schema, request or DesignRequest())

    r = pbigen.generate("parquet", source_config={"uri": orders_parquet}, model=Fixed(),
                        out_dir=str(tmp_path), name="Brief", context="We are a retailer.")
    md = open(r.design_md).read()
    assert "## Business context" in md and "## Storyline" in md and "No cancellation data" in md
    assert md.count("https://a") == 1                                    # sources de-duplicated


def test_legacy_two_argument_models_still_work(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")

    class Legacy(Model):                       # a custom model written against pbigen 0.3
        name = "legacy"

        def design(self, schema, objective):
            return design(schema, objective)

    r = pbigen.generate("parquet", source_config={"uri": orders_parquet}, model=Legacy(),
                        out_dir=str(tmp_path), name="Legacy")
    assert r.n_pages >= 3
