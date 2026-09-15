"""Model routing, theme loading, and the emitter's visual binding.

Author: Arka Gupta
"""
from __future__ import annotations

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


def test_unknown_theme_raises():
    with pytest.raises(ValueError):
        get_theme("no-such-theme")
