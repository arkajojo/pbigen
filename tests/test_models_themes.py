"""Model routing, theme loading, and the emitter's visual binding.

Author: Arka Gupta
"""
from __future__ import annotations

import json

import pytest

from pbigen.core.design import Visual
from pbigen.emit.visuals import build_visual
from pbigen.models import NullModel, get_model
from pbigen.themes import available_themes, get_theme, split_chrome


def test_default_model_is_deterministic():
    assert isinstance(get_model(None), NullModel)
    assert isinstance(get_model("deterministic"), NullModel)


def test_llm_spec_routes_to_litellm_without_calling_it():
    # constructing the model must not require litellm or a network call
    model = get_model("gpt-4o-mini")
    assert model.name == "litellm:gpt-4o-mini"


def test_builtin_theme_has_chrome_colors():
    for name in available_themes():
        theme = get_theme(name)
        clean, sidebar, accent = split_chrome(theme)
        assert sidebar.startswith("#") and accent.startswith("#")
        assert "sidebarColor" not in clean          # chrome hints stripped from the theme doc
        assert "dataColors" in clean


def test_build_visual_binds_measure_and_category():
    v = Visual("bar", "Revenue by region", measures=["Total Revenue"], category="region",
               x=10, y=20, w=300, h=200)
    obj = build_visual(v, "orders", "p0-v00", 3)
    assert obj["visual"]["visualType"] == "clusteredBarChart"
    qs = obj["visual"]["query"]["queryState"]
    assert qs["Y"]["projections"][0]["field"]["Measure"]["Property"] == "Total Revenue"
    assert qs["Category"]["projections"][0]["field"]["Column"]["Property"] == "region"
    assert obj["position"]["width"] == 300


def test_slicer_carries_mode_and_header():
    v = Visual("slicer", "region", category="region", slicer_mode="Dropdown", w=260, h=72)
    obj = build_visual(v, "orders", "p0-s00", 1)
    assert obj["visual"]["visualType"] == "slicer"
    assert obj["visual"]["objects"]["data"][0]["properties"]["mode"]["expr"]["Literal"]["Value"] == "'Dropdown'"


def test_container_title_shown_on_charts_hidden_on_textbox():
    from pbigen.emit.visuals import build_textbox, text_run

    chart = build_visual(Visual("bar", "Revenue by region", measures=["Revenue"], category="region"),
                         "t", "p0-v00", 3)
    title = chart["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert title["show"]["expr"]["Literal"]["Value"] == "true"          # chart shows a themed title
    assert title["text"]["expr"]["Literal"]["Value"] == "'Revenue by region'"

    tb = build_textbox("p0-title", [text_run("Executive Summary")], 0, 0, 100, 40, 1, 4)
    tb_title = tb["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert tb_title["show"]["expr"]["Literal"]["Value"] == "false"      # no empty white header on chrome


def test_theme_file_with_bom_loads(tmp_path):
    # gallery / Windows-exported theme JSONs often start with a UTF-8 BOM
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"name": "BomTheme", "dataColors": ["#112233"]}).encode())
    assert get_theme(str(p))["name"] == "BomTheme"


def test_llm_measures_referencing_missing_columns_are_dropped():
    from pbigen.core.design import design as baseline_design
    from pbigen.core.schema import Column, Schema
    from pbigen.models.litellm_model import _parse

    sch = Schema("orders", [Column("status", "string"), Column("num_of_item", "integer")])
    llm = ('{"measures":[{"name":"Total Orders","agg":"COUNT"},'
           '{"name":"Total Revenue","column":"revenue","agg":"SUM"},'
           '{"name":"Total Items","column":"num_of_item","agg":"SUM"}],'
           '"pages":[{"name":"Exec","visuals":['
           '{"type":"card","measures":["Total Orders"]},'
           '{"type":"card","measures":["Total Revenue"]},'
           '{"type":"bar","category":"status","measures":["Total Items"]}]}]}')
    d = _parse(llm, sch, baseline_design(sch, ""))
    names = [m.name for m in d.measures]
    assert "Total Revenue" not in names          # column 'revenue' doesn't exist -> dropped
    assert {"Total Orders", "Total Items"} <= set(names)
    # the card that referenced the dropped measure is gone (no empty/errored visual)
    assert all("Total Revenue" not in v.measures for v in d.pages[0].visuals)


def test_unknown_theme_raises():
    with pytest.raises(ValueError):
        get_theme("no-such-theme")
