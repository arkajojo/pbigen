"""Template packs: compile a report (.pbix legacy layout, or a PBIP folder) into a design shell,
then generate new data inside it.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import zipfile

import pytest

import pbigen
from pbigen.template.pack import build_pack, load_pack, sanitize_objects


def _lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def _container(vtype, x, y, w, h, z, objects=None, vco=None, data=False):
    sv = {"visualType": vtype, "objects": objects or {}, "vcObjects": vco or {}}
    if data:
        sv["projections"] = {"Values": [{"queryRef": "t.m"}]}
    return {"x": x, "y": y, "width": w, "height": h, "z": z,
            "config": json.dumps({"name": f"{vtype}{x}{y}", "singleVisual": sv})}


@pytest.fixture()
def fake_pbix(tmp_path) -> str:
    """A minimal legacy-format .pbix: left sidebar panel + logo, a big title, slicers in the
    sidebar, cards and charts on the right, a custom theme and a background image."""
    card_style = {"labels": [{"properties": {"fontSize": _lit("30D")}}],
                  # data-bound formatting must NOT survive into the pack
                  "dataPoint": [{"properties": {"fill": _lit("'#ff0000'")},
                                 "selector": {"data": [{"scopeId": {}}]}}]}
    vco = {"border": [{"properties": {"show": _lit("true"), "radius": _lit("16D")}}],
           "title": [{"properties": {"show": _lit("true"), "text": _lit("'Their KPI'")}}]}
    section = {
        "name": "s1", "displayName": "Overview", "width": 1600, "height": 900, "ordinal": 0,
        "config": json.dumps({"objects": {"background": [{"properties": {"image": {"image": {
            "name": _lit("'bg.png'"),
            "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources",
                                                     "PackageType": 1, "ItemName": "bg.png"}}},
            "scaling": _lit("'Fit'")}}}}]}}),
        "visualContainers": [
            _container("shape", 0, 0, 280, 900, 0, {"shape": [{"properties": {"tileShape": _lit("'rectangle'")}}]}),
            _container("image", 40, 20, 200, 90, 1, {"general": [{"properties": {"imageUrl": {"expr": {
                "ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                        "ItemName": "logo.png"}}}}}]}),
            _container("textbox", 320, 20, 900, 70, 2, {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": "Their Big Title", "textStyle": {"fontSize": "32pt",
                                                                         "fontFamily": "DIN"}}]}]}}]}),
            _container("slicer", 20, 150, 240, 60, 3, data=True),
            _container("slicer", 20, 220, 240, 60, 4, data=True),
            _container("card", 320, 120, 380, 140, 5, card_style, vco, data=True),
            _container("card", 720, 120, 380, 140, 6, card_style, vco, data=True),
            _container("lineChart", 320, 280, 1240, 580, 7, {}, vco, data=True),
            # a small icon inside the content area is a per-visual decoration -> dropped
            _container("image", 330, 125, 20, 20, 8),
        ],
    }
    layout = {"config": json.dumps({"themeCollection": {"customTheme": {"name": "brand.json"}}}),
              "sections": [section]}
    theme = {"name": "Brand", "dataColors": ["#123456", "#abcdef"], "foreground": "#0B1F33"}
    path = tmp_path / "their_report.pbix"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
        z.writestr("Report/StaticResources/RegisteredResources/brand.json", json.dumps(theme))
        z.writestr("Report/StaticResources/RegisteredResources/logo.png", b"\x89PNG fake")
        z.writestr("Report/StaticResources/RegisteredResources/bg.png", b"\x89PNG fake")
    return str(path)


def test_build_pack_measures_the_shell(fake_pbix, tmp_path):
    pack = build_pack(fake_pbix, str(tmp_path / "pack"))
    assert (pack.page_w, pack.page_h) == (1600, 900)
    # content = where their data visuals were; filters = their slicer rail; header = their title
    assert pack.content.x == 320 and pack.content.y == 120
    assert pack.filters and pack.filters.x == 20 and pack.filters.h >= 120
    assert pack.header.y == 20 and pack.title_style.font == "DIN" and pack.title_style.size == "32pt"
    # chrome keeps the sidebar panel and the logo, drops the in-content icon
    types = sorted(c.type for c in pack.chrome)
    assert types == ["image", "shape"]
    assert pack.page_objects.get("background")
    assert pack.theme_file == "theme.json" and set(pack.assets) == {"logo.png", "bg.png"}
    # styles keep look-and-feel, drop data-bound formatting and their title text
    card = pack.styles["card"]
    assert "dataPoint" not in card["objects"]
    assert card["objects"]["labels"][0]["properties"]["fontSize"]
    assert "text" not in card["visualContainerObjects"]["title"][0]["properties"]
    # round-trips through pack.json
    again = load_pack(str(tmp_path / "pack"))
    assert again.content == pack.content and again.theme()["name"] == "Brand"


def test_sanitize_strips_bindings():
    objs = {"fill": [{"properties": {"color": {"solid": {"color": {"expr": {"Measure": {"Property": "x"}}}}},
                                     "show": _lit("true")}}]}
    out = sanitize_objects(objs)
    assert out == {"fill": [{"properties": {"show": _lit("true")}}]}


def test_generate_inside_template(orders_parquet, fake_pbix, tmp_path):
    pytest.importorskip("duckdb")
    r = pbigen.generate("parquet", source_config={"uri": orders_parquet}, out_dir=str(tmp_path),
                        name="InTheirShell", template=fake_pbix)
    assert r.template == "their_report"
    rep = tmp_path / "InTheirShell" / "InTheirShell.Report"
    # their theme + the images their shell references are registered
    report = json.loads((rep / "definition" / "report.json").read_text())
    names = {i["name"] for p in report["resourcePackages"] for i in p["items"]}
    assert {"logo.png", "bg.png"} <= names
    assert (rep / "StaticResources" / "RegisteredResources" / "bg.png").exists()
    page_dir = rep / "definition" / "pages" / "Executive-Summary"
    page = json.loads((page_dir / "page.json").read_text())
    assert page["width"] == 1600 and "background" in page.get("objects", {})
    visuals = [json.loads((d / "visual.json").read_text()) for d in (page_dir / "visuals").iterdir()]
    data = [v for v in visuals if v["visual"].get("query")]
    # every data visual lands inside their content region (x >= 320) or slicer rail (x < 280)
    for v in data:
        x = v["position"]["x"]
        assert x >= 320 or (v["visual"]["visualType"] == "slicer" and x < 280)
    # their card look (radius border) is applied to our cards
    cards = [v for v in data if v["visual"]["visualType"] == "card"]
    assert cards and all("border" in c["visual"]["visualContainerObjects"] for c in cards)


def test_generated_project_is_itself_a_template(orders_parquet, tmp_path):
    """A PBIP .Report folder (PBIR) compiles into a pack too — e.g. re-use a report you built."""
    pytest.importorskip("duckdb")
    r = pbigen.generate("parquet", source_config={"uri": orders_parquet}, out_dir=str(tmp_path), name="Base")
    pack = build_pack(r.pbip_path, str(tmp_path / "pack2"))
    assert pack.page_w == 1920 and pack.content.w > 800
    assert os.path.exists(tmp_path / "pack2" / "theme.json")


def test_cli_template_build(fake_pbix, tmp_path, capsys):
    from pbigen.cli import main
    out = str(tmp_path / "clipack")
    assert main(["template", "build", fake_pbix, "--out", out]) == 0
    assert os.path.exists(os.path.join(out, "pack.json"))
    assert main(["template", "show", out]) == 0
    assert "canvas      1600 x 900" in capsys.readouterr().out
