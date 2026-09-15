"""Source registry.

``get_source(kind, **cfg)`` returns a configured adapter. Adapters are imported lazily so that
installing a single extra (e.g. ``dashforge[bigquery]``) is enough to use that one source without
pulling every driver.

Author: Arka Gupta
"""
from __future__ import annotations

from typing import Any

from .base import ConnectionTest, Source

# kind -> (module, class). One canonical name per source, with friendly aliases.
_REGISTRY: dict[str, tuple[str, str]] = {
    "bigquery": ("dashforge.sources.bigquery", "BigQuerySource"),
    "biglake": ("dashforge.sources.bigquery", "BigQuerySource"),
    "bigquery_omni": ("dashforge.sources.bigquery", "BigQuerySource"),
    "postgres": ("dashforge.sources.warehouses", "PostgresSource"),
    "redshift": ("dashforge.sources.warehouses", "RedshiftSource"),
    "snowflake": ("dashforge.sources.warehouses", "SnowflakeSource"),
    "synapse": ("dashforge.sources.warehouses", "SynapseSource"),
    "fabric": ("dashforge.sources.warehouses", "SynapseSource"),
    "databricks": ("dashforge.sources.warehouses", "DatabricksSource"),
    "clickhouse": ("dashforge.sources.warehouses", "ClickHouseSource"),
    "athena": ("dashforge.sources.warehouses", "AthenaSource"),
    "lakehouse": ("dashforge.sources.lakehouse", "LakehouseSource"),
    "parquet": ("dashforge.sources.lakehouse", "LakehouseSource"),
    "iceberg": ("dashforge.sources.lakehouse", "LakehouseSource"),
    "delta": ("dashforge.sources.lakehouse", "LakehouseSource"),
    "cube": ("dashforge.sources.cube", "CubeSource"),
}

# kinds that fix the lakehouse ``fmt`` for the caller
_LAKEHOUSE_FMT = {"parquet": "parquet", "iceberg": "iceberg", "delta": "delta"}


def available_kinds() -> list[str]:
    return sorted(_REGISTRY)


def get_source(kind: str, **cfg: Any) -> Source:
    key = kind.lower().replace("-", "_")
    if key not in _REGISTRY:
        raise ValueError(f"unknown source {kind!r}; available: {', '.join(available_kinds())}")
    module_name, class_name = _REGISTRY[key]
    import importlib
    cls = getattr(importlib.import_module(module_name), class_name)
    if key in _LAKEHOUSE_FMT:
        cfg.setdefault("fmt", _LAKEHOUSE_FMT[key])
    return cls(**cfg)


__all__ = ["Source", "ConnectionTest", "get_source", "available_kinds"]
