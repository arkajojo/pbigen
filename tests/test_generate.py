"""End-to-end generation: Parquet source -> a valid, well-formed Power BI project.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os

import pytest

import dashforge


def test_generate_writes_openable_project(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    result = dashforge.generate(
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

    # measures made it into the TMDL as DAX
    tmdl = (root / "OrdersDemo.SemanticModel" / "definition" / "tables" / "orders.tmdl").read_text()
    assert "SUM('orders'[revenue])" in tmdl
    assert "partition 'orders' = m" in tmdl


def test_generate_with_custom_theme_file(orders_parquet, tmp_path):
    pytest.importorskip("duckdb")
    theme = tmp_path / "corp.json"
    theme.write_text(json.dumps({"name": "CorpTheme", "dataColors": ["#123456", "#654321"]}))
    dashforge.generate(
        "parquet", source_config={"uri": orders_parquet},
        theme=str(theme), out_dir=str(tmp_path), name="Corp",
    )
    registered = (tmp_path / "Corp" / "Corp.Report" / "definition"
                  / "StaticResources" / "RegisteredResources")
    assert any(registered.glob("*.json"))
    report = json.loads((tmp_path / "Corp" / "Corp.Report" / "definition" / "report.json").read_text())
    assert report["themeCollection"]["customTheme"]["name"] == "CorpTheme"
