"""dashforge — generate world-class Power BI dashboards from any data source.

Point it at a table (BigQuery, Snowflake, Redshift, Synapse/Fabric, Databricks, ClickHouse,
Athena, a Parquet/Iceberg/Delta lake on GCS/S3/ADLS, or a Cube semantic layer), and it
introspects the schema, reasons about the data shape, and writes an openable Power BI project:
a navigation sidebar, data-appropriate charts and filters, and usage notes.

    import dashforge

    result = dashforge.generate(
        "bigquery",
        source_config={"project": "my-proj", "dataset": "sales", "table": "orders"},
        objective="Revenue and orders by region over time",
        theme="midnight",
        out_dir="out",
    )
    print(result.pbip_path)

The design defaults to a deterministic, no-key engine. Pass ``model="gpt-4o-mini"`` (or any
LiteLLM model id, hosted or local) to let a language model refine the design; only metadata is
ever sent to it.

Author: Arka Gupta
"""
from __future__ import annotations

from .core.generator import GenerateResult, generate
from .sources import available_kinds, get_source
from .themes import available_themes, get_theme

__version__ = "0.1.0"
__author__ = "Arka Gupta"

__all__ = [
    "generate", "GenerateResult",
    "get_source", "available_kinds",
    "get_theme", "available_themes",
    "__version__",
]
