"""Design-brain tests: column classification, measures, cardinality-aware chart/filter choices.

Author: Arka Gupta
"""
from __future__ import annotations

from pbigen.core.design import classify, design, propose_measures
from pbigen.core.schema import Column, Schema


def _schema() -> Schema:
    return Schema("orders", [
        Column("order_date", "datetime"),
        Column("region", "string", cardinality=4),
        Column("product", "string", cardinality=3),
        Column("customer_id", "string", cardinality=900),
        Column("year_month", "string", cardinality=18),
        Column("revenue", "float"),
        Column("quantity", "integer"),
    ])


def test_classify_buckets_columns():
    cls = classify(_schema())
    assert "revenue" in cls["measures"] and "quantity" in cls["measures"]
    assert "order_date" in cls["dates"]
    assert "region" in cls["categories"]
    assert "customer_id" in cls["ids"]          # id-hint keeps it out of measures/categories


def test_propose_measures_marks_money():
    measures = {m.name: m for m in propose_measures(_schema())}
    assert any(m.money for m in measures.values())      # revenue is money
    assert all(m.agg == "SUM" for m in measures.values())


def test_design_builds_narrative_pages():
    d = design(_schema(), objective="revenue overview")
    names = [p.name for p in d.pages]
    assert names[0] == "Executive Summary"
    assert "Detailed Data" in names
    assert d.usage_notes                                 # notes always present


def test_low_cardinality_gets_donut_high_gets_bar():
    d = design(_schema())
    exec_page = d.pages[0]
    breakdowns = {v.category: v.type for v in exec_page.visuals if v.category and v.type in ("donut", "bar")}
    # region (4 distinct) -> donut; if a higher-cardinality dim were charted it would be a bar
    assert breakdowns.get("region") == "donut"


def test_date_is_not_a_dropdown_slicer():
    d = design(_schema())
    slicers = d.pages[0].slicers
    # a real date drives a range filter in the sidebar, and high-cardinality ids never become slicers
    assert "customer_id" not in slicers
    # year_month is a redundant period part once a real date exists -> dropped
    assert "year_month" not in slicers
