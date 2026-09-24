"""pbigen — your report's design, your data's story: Power BI dashboards generated.

Point it at a table (BigQuery, Snowflake, Redshift, Synapse/Fabric, Databricks, ClickHouse,
Athena, a Parquet/Iceberg/Delta lake on GCS/S3/ADLS, or a Cube semantic layer) and, optionally, at
a ``.pbix`` whose design you want to reuse. It introspects the schema, designs a structured story
(deterministically, or with a staged AI pipeline: business context -> objectives & KPI tree ->
research -> storyboard -> critique) and writes an openable Power BI project plus a ``DESIGN.md``.

    import pbigen

    result = pbigen.generate(
        "bigquery",
        source_config={"project": "my-proj", "dataset": "sales", "table": "orders"},
        template="company_standard.pbix",      # or a pack from `pbigen template build`
        model="gpt-4o", research="web",        # omit model for the deterministic engine
        context="D2C retailer focused on profitable growth",
        out_dir="out",
    )
    print(result.pbip_path, result.design_md)

Only metadata is ever sent to a model (plus aggregate profiles if you pass ``profile=True``).

Author: Arka Gupta
"""
from __future__ import annotations

from .core.generator import GenerateResult, generate
from .sources import available_kinds, get_source
from .themes import available_themes, get_theme

__version__ = "0.4.0"
__author__ = "Arka Gupta"

__all__ = [
    "generate", "GenerateResult",
    "get_source", "available_kinds",
    "get_theme", "available_themes",
    "__version__",
]
