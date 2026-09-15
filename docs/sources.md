# Sources

Every source implements the same three-method contract, so the design engine and the emitter
never care which system the data came from:

1. **introspect** — read the table's columns and canonical types (metadata only, never rows).
2. **approx_distinct** — approximate distinct counts, so the design can pick data-appropriate
   charts and filters.
3. **power_query** — the Power Query (M) the generated model uses to connect at refresh time.

All adapters are **read-only** and lazy: importing an adapter never opens a connection, and drivers
are imported only when you actually use that source. Install just the extra you need.

```bash
dashforge sources                                  # list every kind
dashforge test --source <kind> --set key=value ...  # verify connectivity + introspection
```

## Canonical types

Native types are normalised to: `string`, `integer`, `float`, `decimal`, `boolean`, `date`,
`datetime`, `time`. The design engine reasons in these terms; the emitter maps them to Power BI
model types.

## Warehouses & engines (SQLAlchemy-backed)

| Kind | Install | Key config (`--set`) | Env fallbacks |
|------|---------|----------------------|---------------|
| `postgres` | `dashforge[postgres]` | `table host port database schema user password` | `PGUSER`, `PGPASSWORD` |
| `redshift` | `dashforge[redshift]` | `table host port database schema user password` | `REDSHIFT_HOST/USER/PASSWORD` |
| `snowflake` | `dashforge[snowflake]` | `table account warehouse database schema user password role` | `SNOWFLAKE_*` |
| `synapse` / `fabric` | `dashforge[synapse]` | `table server database schema user password` | `SYNAPSE_SERVER/DATABASE/USER/PASSWORD` |
| `databricks` | `dashforge[databricks]` | `table host http_path token catalog schema` | `DATABRICKS_HOST/HTTP_PATH/TOKEN` |
| `clickhouse` | `dashforge[clickhouse]` | `table host port database user password secure` | `CLICKHOUSE_HOST/USER/PASSWORD` |
| `athena` | `dashforge[athena]` | `table region database s3_staging_dir workgroup` | `AWS_REGION`, `ATHENA_S3_STAGING_DIR` |

`synapse` also covers **Microsoft Fabric** (SQL analytics endpoint) and SQL Server — all speak T-SQL.

## BigQuery / BigLake / BigQuery Omni

```bash
pip install "dashforge[bigquery]"
dashforge generate --source bigquery \
  --set project=my-proj dataset=sales table=orders
```

BigLake (external data in GCS with governance) and BigQuery Omni (data in S3/ADLS queried through
BigQuery) are ordinary BigQuery relations — they use the same adapter and connector. Auth uses
Application Default Credentials (`gcloud auth application-default login`) or a service account.

## Lakehouse: Parquet, Iceberg, Delta on local / GCS / S3 / ADLS

A single DuckDB-powered adapter reads open table formats with no cluster:

```bash
pip install "dashforge[lakehouse]"

dashforge generate --source parquet --set uri=./sales.parquet
dashforge generate --source iceberg --set uri=s3://bucket/warehouse/db/orders
dashforge generate --source delta   --set uri=abfss://data@acct.dfs.core.windows.net/orders
```

Cloud credentials are read from the environment and turned into DuckDB secrets automatically:

- **S3**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- **GCS**: `GCS_HMAC_KEY_ID`, `GCS_HMAC_SECRET`
- **ADLS**: `AZURE_STORAGE_CONNECTION_STRING`

**Refresh note.** Introspection is fully portable. For the *generated report to refresh*, raw
Parquet is reachable through Power BI's storage connectors; Iceberg and Delta are best consumed via
a **Fabric Lakehouse** or **Databricks SQL** endpoint — point the `databricks` / `synapse` adapter
at that endpoint, or expose the table through a Fabric shortcut. The emitted M for Iceberg/Delta
carries a comment explaining this.

## Cube (semantic layer)

```bash
pip install "dashforge[cube]"
dashforge generate --source cube \
  --set cube=Orders api_url=https://cube.example.com/cubejs-api/v1 sql_host=cube.example.com
```

Reading from Cube means the report inherits your governed measures and dimensions instead of
re-deriving them. Introspection uses Cube's `/meta` API; Power BI connects through Cube's SQL API
(PostgreSQL wire protocol). Set `CUBE_API_URL`, `CUBE_API_TOKEN`, `CUBE_SQL_HOST`, `CUBE_SQL_USER`,
`CUBE_SQL_PASSWORD` in the environment if you prefer not to pass them inline.

## Opening the result in Power BI Desktop

The output is a **PBIP** project. In Power BI Desktop enable, once:

**File → Options → Preview features → "Store reports using enhanced metadata format (PBIR)"**,
then restart. Open the `.pbip`, and refresh to load data through the generated connection.
