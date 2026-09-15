"""End-to-end generation: Parquet source -> a valid, well-formed Power BI project.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os

import pytest

import pbigen


def test_generate_writes_openable_project(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    result = pbigen.generate(
        "parquet",
        source_config={"uri": orders_parquet},
        objective="Revenue and orders by region over time",
        theme="midnight",
        out_dir=str(tmp_path),
        name="OrdersDemo",
    )
    assert result.n_pages >= 3
    assert result.model_name == "deterministic"
    assert os.path.exists(result.pbip_path)

    root = tmp_path / "OrdersDemo"
    # report + semantic model both present
    assert (root / "OrdersDemo.Report" / "definition.pbir").exists()
    assert (root / "OrdersDemo.SemanticModel" / "definition" / "tables" / "orders.tmdl").exists()

    # every emitted report JSON parses and declares a fabric schema
    defn = root / "OrdersDemo.Report" / "definition"
    seen_schema = 0
    for path in defn.rglob("*.json"):
        obj = json.loads(path.read_text())
        if "$schema" in obj:
            assert "developer.microsoft.com" in obj["$schema"]
            seen_schema += 1
    assert seen_schema > 5

    # version.json must carry its $schema (Power BI Desktop refuses to load without it)
    version = json.loads((defn / "version.json").read_text())
    assert version["$schema"].endswith("/versionMetadata/1.0.0/schema.json")
    assert version["version"] == "2.0.0"

    # measures made it into the TMDL as DAX
    tmdl = (root / "OrdersDemo.SemanticModel" / "definition" / "tables" / "orders.tmdl").read_text()
    assert "SUM('orders'[revenue])" in tmdl
    assert "partition 'orders' = m" in tmdl


def test_generate_with_custom_theme_file(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    theme = tmp_path / "corp.json"
    theme.write_text(json.dumps({"name": "CorpTheme", "dataColors": ["#123456", "#654321"]}))
    pbigen.generate(
        "parquet", source_config={"uri": orders_parquet},
        theme=str(theme), out_dir=str(tmp_path), name="Corp",
    )
    # StaticResources sits at the .Report root (sibling of definition/), or Power BI ignores the theme
    registered = (tmp_path / "Corp" / "Corp.Report" / "StaticResources" / "RegisteredResources")
    theme_files = [p.name for p in registered.glob("*.json")]
    assert theme_files, "custom theme not written as a registered resource"
    theme_file = theme_files[0]                      # e.g. "CorpTheme.json"

    report = json.loads((tmp_path / "Corp" / "Corp.Report" / "definition" / "report.json").read_text())
    tc = report["themeCollection"]
    # customTheme is named by the registered FILE name, and sits on a base theme, both declared
    assert tc["customTheme"]["name"] == theme_file
    assert tc["baseTheme"]["name"]                    # a base theme is present
    reg_pkg = next(p for p in report["resourcePackages"] if p["type"] == "RegisteredResources")
    assert reg_pkg["items"][0]["path"] == theme_file


def test_generate_right_nav_and_logo(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    logo = tmp_path / "logo.png"
    logo.write_bytes(bytes.fromhex("89504e470d0a1a0a"))     # PNG magic — enough for a file copy
    pbigen.generate("parquet", source_config={"uri": orders_parquet},
                    theme="midnight", nav="right", logo=str(logo),
                    out_dir=str(tmp_path), name="Shell")
    report = tmp_path / "Shell" / "Shell.Report"
    # sidebar shape sits on the right half of the canvas
    import glob
    navs = glob.glob(str(report / "definition" / "pages" / "*" / "visuals" / "*nav*" / "visual.json"))
    x = json.loads(open(navs[0]).read())["position"]["x"]
    assert x > 1000, "right nav sidebar should be on the right side of the 1920px canvas"
    # logo copied + declared as an Image resource
    assert (report / "StaticResources" / "RegisteredResources" / "logo.png").exists()
    rep = json.loads((report / "definition" / "report.json").read_text())
    images = [i for p in rep["resourcePackages"] if p["type"] == "RegisteredResources"
              for i in p["items"] if i["type"] == "Image"]
    assert images and images[0]["path"] == "logo.png"


def test_extract_template_from_pbix(tmp_path):
    import json as _json
    import zipfile
    pbix = tmp_path / "their.pbix"
    with zipfile.ZipFile(pbix, "w") as z:
        z.writestr("Report/StaticResources/RegisteredResources/brand.json",
                   _json.dumps({"name": "Brand", "dataColors": ["#AA0000"]}))
        z.writestr("Report/StaticResources/RegisteredResources/logo.png", b"\x89PNG")
    from pbigen.reference import extract_template
    r = extract_template(str(pbix), str(tmp_path / "tmpl"))
    assert r.theme_path and json.loads(open(r.theme_path).read())["name"] == "Brand"
    assert "logo.png" in r.images


def test_generate_directquery_sets_partition_mode(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    pbigen.generate("parquet", source_config={"uri": orders_parquet},
                    mode="directquery", out_dir=str(tmp_path), name="DQ")
    tables = (tmp_path / "DQ" / "DQ.SemanticModel" / "definition" / "tables")
    tmdl = next(tables.glob("*.tmdl")).read_text()
    assert "mode: directQuery" in tmdl                  # default is import; here we asked for DQ
