# Sources — connect, authenticate, test

Every source implements the same read-only contract, so the design engine and the emitter never
care which system the data came from:

1. **introspect()** — read the table's columns and canonical types (**metadata only**, never rows).
2. **approx_distinct()** — approximate distinct counts, so the design picks data-appropriate charts/filters.
3. **power_query()** — the Power Query (M) the generated model uses to connect at refresh time.

All adapters are **read-only** and import their driver lazily, so installing one extra is enough to
use that one source.

## The universal flow (every source)

```bash
pip install "pbigen[<extra>]"          # 1. install just the driver you need
# 2. authenticate (per-source, below) — usually environment variables
pbigen test    --source <kind> --set <key=value ...>     # 3. verify connectivity + introspection
pbigen generate --source <kind> --set <key=value ...> \  # 4. generate (deterministic by default)
  --theme midnight --out out
# 5. add a model to let an LLM refine the design (optional): --model <id>   (see docs/models.md)
# 6. open out/<name>/<name>.pbip in Power BI Desktop (enable the PBIR preview) and Refresh
```

- `--set` passes adapter config as `key=value` pairs; most values also fall back to an environment variable.
- `pbigen test` is the fast, safe first check — it only reads metadata.
- `pbigen sources` lists every kind; `pbigen themes` lists built-in themes.

## Canonical types

Native types normalise to: `string`, `integer`, `float`, `decimal`, `boolean`, `date`, `datetime`,
`time`. The design engine reasons in these; the emitter maps them to Power BI model types.

---

# GCP

## BigQuery / BigLake / BigQuery Omni — kind `bigquery` · extra `pbigen[bigquery]`

BigLake (governed external data in GCS) and BigQuery Omni (data in S3/ADLS queried through BigQuery)
are ordinary BigQuery relations — same adapter, same connector.

**Authenticate** (either):
```bash
# A) Application Default Credentials (interactive, best for a laptop):
gcloud auth application-default login
# B) Service account key (best for CI/servers):
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```
**IAM the identity needs:** `roles/bigquery.dataViewer` on the dataset (read schema) and
`roles/bigquery.jobUser` on the billing project (run the cardinality query).

**Configure (`--set`):** `project` `dataset` `table` · optional `billing_project` (env
`BQ_BILLING_PROJECT`, defaults to `project`), `location`.

```bash
pbigen test --source bigquery --set project=my-proj dataset=sales table=orders
pbigen generate --source bigquery --set project=my-proj dataset=sales table=orders \
  --theme midnight --out out
```

---

# AWS

## Redshift — kind `redshift` · extra `pbigen[redshift]`

**Authenticate:** database user + password.
```bash
export REDSHIFT_HOST=my-cluster.abc123.us-east-1.redshift.amazonaws.com
export REDSHIFT_USER=analytics_ro
export REDSHIFT_PASSWORD=…
```
(For Redshift Serverless, `REDSHIFT_HOST` is the workgroup endpoint.) The user needs `SELECT` on the
table and `USAGE` on the schema. Network: the host must be reachable (VPC/SG/allow-list or a tunnel).

**Configure:** `table` · optional `host` `port` (5439) `database` (dev) `schema` (public) `user` `password`.
```bash
pbigen test --source redshift --set table=orders database=analytics schema=sales
```

## Athena — kind `athena` · extra `pbigen[athena]`

Presto/Trino SQL over data in S3, catalogued in Glue.

**Authenticate:** the **standard AWS credential chain** — any of:
```bash
export AWS_ACCESS_KEY_ID=…   AWS_SECRET_ACCESS_KEY=…   AWS_SESSION_TOKEN=…   # temp creds
# or:  aws configure           (writes ~/.aws/credentials; pick a profile with AWS_PROFILE)
# or:  an attached IAM role (EC2/ECS/Lambda) — nothing to set
export AWS_REGION=us-east-1
export ATHENA_S3_STAGING_DIR=s3://my-athena-results/     # where Athena writes query output
```
**IAM the identity needs:** `athena:StartQueryExecution`/`GetQueryResults`, Glue catalog read
(`glue:GetTable`/`GetDatabase`), S3 read on the data, and S3 read/write on the staging bucket.

**Configure:** `table` · optional `region` `database` (default) `s3_staging_dir` `workgroup` (primary).
```bash
pbigen test --source athena --set table=orders database=analytics \
  s3_staging_dir=s3://my-athena-results/ region=us-east-1
```

---

# Azure

## Synapse / Microsoft Fabric / SQL Server — kind `synapse` (alias `fabric`) · extra `pbigen[synapse]`

All speak T-SQL over ODBC.

**OS prerequisite — install the Microsoft ODBC Driver 18** (pyodbc needs it):
```bash
# macOS:
brew tap microsoft/mssql-release https://github.com/microsoft/homebrew-mssql-release
brew install msodbcsql18
# Debian/Ubuntu: follow https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
```
**Authenticate:** SQL login (simplest) — server + database + user + password (connection is encrypted):
```bash
export SYNAPSE_SERVER=myworkspace.sql.azuresynapse.net      # or the Fabric SQL analytics endpoint
export SYNAPSE_DATABASE=analytics
export SYNAPSE_USER=analytics_ro
export SYNAPSE_PASSWORD=…
```
For **Fabric** point `SYNAPSE_SERVER` at the warehouse/lakehouse **SQL analytics endpoint**
(Fabric → your item → *Copy SQL connection string*). Azure AD auth is possible by adding driver
params (e.g. an `Authentication=…` option in `driver=`) — SQL auth is the quickest path to a first test.

**Configure:** `table` · optional `server` `database` `schema` (dbo) `user` `password` `driver`.
```bash
pbigen test --source synapse --set table=orders schema=dbo
```

## Databricks — kind `databricks` · extra `pbigen[databricks]`

Works for Azure Databricks and Databricks on AWS/GCP — anywhere with a SQL warehouse.

**Authenticate:** host + HTTP path + a **personal access token**.
- Host + HTTP path: SQL warehouse → **Connection details** (`Server hostname`, `HTTP path`).
- Token: **Settings → Developer → Access tokens → Generate**.
```bash
export DATABRICKS_HOST=adb-1234567890.11.azuredatabricks.net
export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123def456
export DATABRICKS_TOKEN=dapi…
```
**Configure:** `table` · optional `host` `http_path` `token` `catalog` (hive_metastore) `schema` (default).
```bash
pbigen test --source databricks --set table=orders catalog=main schema=sales
```

---

# Multi-cloud / other

## Snowflake — kind `snowflake` · extra `pbigen[snowflake]`

**Authenticate:** account + user + password + a warehouse (needed to run the cardinality query).
```bash
export SNOWFLAKE_ACCOUNT=ORG-ACCOUNT      # e.g. xy12345 or myorg-myacct
export SNOWFLAKE_USER=ANALYTICS_RO
export SNOWFLAKE_PASSWORD=…
export SNOWFLAKE_WAREHOUSE=BI_WH
export SNOWFLAKE_DATABASE=ANALYTICS
export SNOWFLAKE_ROLE=ANALYST            # optional
```
The role needs `USAGE` on the warehouse/database/schema and `SELECT` on the table.

**Configure:** `table` · optional `account` `warehouse` `database` `schema` (PUBLIC) `user` `password` `role`.
```bash
pbigen test --source snowflake --set table=ORDERS database=ANALYTICS schema=SALES
```

## PostgreSQL — kind `postgres` · extra `pbigen[postgres]`

**Authenticate:** user + password.
```bash
export PGUSER=analytics_ro
export PGPASSWORD=…
```
**Configure:** `table` · optional `host` (localhost) `port` (5432) `database` (postgres) `schema` (public) `user` `password`.
```bash
pbigen test --source postgres --set table=orders host=db.internal database=analytics schema=sales
```

## ClickHouse — kind `clickhouse` · extra `pbigen[clickhouse]`

**Authenticate:** host + user + password (TLS on 8443/9440).
```bash
export CLICKHOUSE_HOST=abc.clickhouse.cloud
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=…
```
**Configure:** `table` · optional `host` `port` (8443) `database` (default) `user` `password` `secure` (true).
```bash
pbigen test --source clickhouse --set table=orders database=analytics port=8443 secure=true
```

---

# Lakehouse — Parquet, Iceberg, Delta on local / GCS / S3 / ADLS

One DuckDB-powered adapter — kinds `parquet`, `iceberg`, `delta` (or `lakehouse` with `fmt=`) ·
extra `pbigen[lakehouse]`. No cluster needed for introspection.

**Local (no auth):**
```bash
pbigen test --source parquet --set uri=./sales.parquet
pbigen generate --source parquet --set uri=./sales.parquet --theme midnight --out out
```
**S3** — standard AWS creds:
```bash
export AWS_ACCESS_KEY_ID=…  AWS_SECRET_ACCESS_KEY=…  AWS_REGION=us-east-1
pbigen test --source iceberg --set uri=s3://bucket/warehouse/db/orders
```
**GCS** — HMAC keys (Cloud Storage → *Settings → Interoperability → Access keys for your user/SA*):
```bash
export GCS_HMAC_KEY_ID=GOOG…  GCS_HMAC_SECRET=…
pbigen test --source delta --set uri=gs://bucket/warehouse/orders
```
**ADLS** — a storage connection string (Storage account → *Access keys → Connection string*):
```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=…;AccountKey=…"
pbigen test --source parquet --set uri="abfss://data@acct.dfs.core.windows.net/orders/*.parquet"
```
`fmt` is inferred from the kind (`parquet`/`iceberg`/`delta`); with kind `lakehouse` pass `fmt=` explicitly.

> **Refresh note.** Introspection is fully portable. For the generated report to *refresh*, raw
> Parquet is reachable via Power BI's storage connectors; **Iceberg/Delta** are best refreshed
> through a **Fabric Lakehouse** or **Databricks SQL** endpoint (point the `databricks`/`synapse`
> adapter at that endpoint, or expose the table via a Fabric shortcut). The emitted M for
> Iceberg/Delta carries a comment explaining this.

---

# Semantic layer

## Cube — kind `cube` · extra `pbigen[cube]`

Reads governed measures/dimensions from [Cube](https://cube.dev) instead of re-deriving them.

**Authenticate:** the REST `/meta` API needs the base URL + an API token (JWT); the SQL API (used for
optional cardinality + the Power BI connection) uses the Cube SQL credentials.
```bash
export CUBE_API_URL=https://cube.example.com/cubejs-api/v1
export CUBE_API_TOKEN=eyJhbGciOi…            # a Cube JWT
export CUBE_SQL_HOST=cube.example.com        # Cube SQL API host
export CUBE_SQL_USER=…   CUBE_SQL_PASSWORD=…
```
**Configure:** `cube` (the cube name) · optional `api_url` `api_token` `sql_host` `sql_port` (15432)
`sql_database` (cube) `sql_user` `sql_password`.
```bash
pbigen test --source cube --set cube=Orders
```

---

# Opening the generated project in Power BI Desktop

The output is a **PBIP** project. One-time in Power BI Desktop:
**File → Options and settings → Options → Preview features → tick "Store reports using enhanced
metadata format (PBIR)"** → restart. Then open the `.pbip` and **Refresh** to load data through the
generated connection.

For a full end-to-end verification harness (deterministic vs. LLM, built-in vs. custom theme, with
schema validation), see **[testing.md](testing.md)**. To use a language model, see
**[models.md](models.md)**.
