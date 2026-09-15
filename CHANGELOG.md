# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to semantic versioning.

## [0.1.0] — Unreleased

Initial release.

### Added

- Source adapters with one read-only introspect / cardinality / connect contract:
  - BigQuery, BigLake, BigQuery Omni
  - Redshift, Athena, Snowflake, Synapse/Fabric, Databricks, ClickHouse, PostgreSQL
  - Parquet, Apache Iceberg and Delta Lake on local disk, GCS, S3 or ADLS (DuckDB)
  - Cube semantic layer
- Deterministic, cardinality-aware design engine (charts and filters chosen from data shape).
- Optional LLM design refinement through LiteLLM (bring your own hosted or local model); metadata
  only, with schema-validated output and graceful fallback.
- Power BI emitter producing an openable PBIP project: PBIR report with a navigation sidebar,
  KPI cards, data-appropriate visuals and usage notes, plus a TMDL semantic model wired to the
  source. Output validates against Microsoft's published PBIR schemas.
- Built-in themes (midnight, slate, aurora) and bring-your-own Power BI theme JSON support.
- `dashforge` CLI (`generate`, `test`, `sources`, `themes`) and a `dashforge.generate()` Python API.
