# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to semantic versioning.

## [0.1.2]

### Fixed

- **BigQuery refresh on locked-down networks.** The generated Power Query now sets
  `UseStorageApi=false`, so refresh falls back to the REST API instead of the BigQuery Storage Read
  API — fixing `Storage API Error: failed to connect to all addresses` where a firewall blocks the
  storage endpoint.
- **Numeric geo/id codes are no longer summed into nonsense measures.** Census tracts, community
  areas, lat/long, ward/district/FIPS/zip codes are classified as geographies, not measures — no
  more "Total Pickup Census Tract".
- **No more "too many columns in the Legend bucket".** A field is only placed on a chart legend /
  matrix column when it has very few distinct values; high-cardinality dimensions become a bar
  category instead.

### Changed

- **Cleaner, more executive design.** Every table leads with a guaranteed-populated **Record Count**
  KPI; rate/ratio columns are averaged (not summed); charts use fewer measures with clear single-
  subject titles ("Revenue by Region"); the detail table is focused rather than every-field.

## [0.1.1]

### Fixed

- **Reports now open in Power BI Desktop.** `version.json` was missing its `$schema`, which current
  Desktop rejects on load ("Can't find '$schema' property in 'version.json'"). It is now written
  with the `versionMetadata/1.0.0` schema.
- **Custom themes now apply.** The report is written with a base theme + a `customTheme` named by its
  registered-resource **file name**, plus the `resourcePackages` declaration Power BI expects — the
  previous output named the theme by its display name and omitted the resource package, so the theme
  failed to resolve.

### Changed

- **Honest model reporting.** When an LLM can't be reached and generation falls back to the
  deterministic design, the result now says so (e.g. `deterministic (fallback — … did not run …)`)
  instead of reporting the requested model as if it ran. The model backend also prints a one-line
  reason to stderr on fallback.

## [0.1.0]

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
- `pbigen` CLI (`generate`, `test`, `sources`, `themes`) and a `pbigen.generate()` Python API.
