"""Source-adapter tests that run fully offline (Parquet via DuckDB, SQLite via SQLAlchemy).

Author: Arka Gupta
"""
from __future__ import annotations

import pytest

from dashforge.sources import available_kinds, get_source


def test_registry_lists_all_clouds():
    kinds = set(available_kinds())
    for expected in ("bigquery", "redshift", "snowflake", "synapse", "databricks",
                     "clickhouse", "athena", "parquet", "iceberg", "delta", "cube"):
        assert expected in kinds


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        get_source("does-not-exist")


def test_lakehouse_introspects_parquet(orders_parquet):
    pytest.importorskip("duckdb")
    src = get_source("parquet", uri=orders_parquet)
    result = src.test_connection()
    assert result.ok, result.message
    schema = src.schema_with_cardinality()
    types = {c.name: c.dtype for c in schema.columns}
    assert types["revenue"] == "float"
    assert types["order_date"] == "date"
    region = schema.by_name("region")
    assert region.cardinality == 4                       # low cardinality detected
    assert "GoogleBigQuery" not in src.power_query()     # parquet M, not a warehouse M
    assert "Parquet.Document" in src.power_query()


def test_sql_source_introspects_sqlite(sqlite_url):
    pytest.importorskip("sqlalchemy")
    from dashforge.sources.sql_base import SqlSource

    src = SqlSource(sqlite_url, "orders")
    schema = src.introspect()
    assert set(schema.names()) == {"region", "product", "revenue", "quantity"}
    counts = src.approx_distinct(["region"])
    assert counts["region"] == 3
