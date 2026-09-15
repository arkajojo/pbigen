# dashforge

**Generate world-class Power BI dashboards from any data source — automatically.**

Point dashforge at a table or view. It reads the schema, reasons about the *shape* of the data
(types, cardinality), and writes a ready-to-open Power BI project: a left navigation sidebar with
your brand and filters, data-appropriate charts, KPI cards, a detail table, and a "how to use this
report" note — laid out cleanly, every time.

No hand-built templates. No copy-pasting M queries. No guesswork about which chart fits which column.

```bash
pip install dashforge
```

```python
import dashforge

result = dashforge.generate(
    "bigquery",
    source_config={"project": "my-proj", "dataset": "sales", "table": "orders"},
    objective="Revenue and orders by region over time",
    theme="midnight",
    out_dir="out",
)
print(result.pbip_path)   # open this in Power BI Desktop
```

or from the terminal:

```bash
dashforge generate --source snowflake \
  --set account=ab12345 database=ANALYTICS schema=SALES table=ORDERS warehouse=BI_WH \
  --objective "Sales performance by region and product" \
  --theme midnight --out out
```

## Why

Building a good Power BI report by hand is slow and inconsistent: someone picks the charts, wires
every field, styles every visual, and writes the connection query. dashforge does the mechanical
90% correctly and consistently, so you spend your time on the last 10% that actually needs a human.

It is opinionated about *good defaults* — cardinality-aware chart selection, a date column becomes
a range filter (never a 500-row dropdown), wide breakdowns go in a matrix, KPIs lead each page —
and unopinionated about *your stack*: bring your own warehouse, your own model, and your own theme.

## Sources

One consistent adapter interface across all of them (introspect → cardinality → connect):

| Cloud | Sources |
|-------|---------|
| **GCP** | BigQuery, BigLake, BigQuery Omni; Parquet / Iceberg / Delta in GCS |
| **AWS** | Redshift, Athena; Parquet / Iceberg / Delta in S3 |
| **Azure** | Synapse, Fabric (SQL endpoint); Parquet / Iceberg / Delta in ADLS |
| **Multi / other** | Snowflake, Databricks, ClickHouse, PostgreSQL |
| **Semantic layer** | Cube |

Lakehouse formats (Parquet, Apache Iceberg, Delta Lake) are read on local disk or any of the three
clouds through a single DuckDB-powered adapter — no cluster required for introspection.

```bash
dashforge sources          # list every source kind
dashforge test --source lakehouse --set uri=./sales.parquet fmt=parquet
```

Install only what you need:

```bash
pip install "dashforge[bigquery]"      # or [snowflake], [redshift], [databricks], [lakehouse], ...
pip install "dashforge[all]"           # everything
```

## Models: deterministic by default, LLM optional

Out of the box, dashforge designs dashboards with a **deterministic, no-key engine** — no network
call, no cost, fully reproducible. If you want a language model to refine the design, pass any
[LiteLLM](https://github.com/BerriAI/litellm) model id (hosted or a local open-source model):

```python
dashforge.generate("bigquery", source_config={...},
                   model="gpt-4o-mini")                    # bring your own key via env
dashforge.generate("bigquery", source_config={...},
                   model="ollama/llama3",                  # fully local, open-source
                   model_config={"api_base": "http://localhost:11434"})
```

**Only metadata is ever sent to a model** — column names, canonical types and approximate distinct
counts. No row data leaves your machine.

## Themes: bring your own, or use a built-in

```python
dashforge.generate(..., theme="midnight")            # built-in: midnight | slate | aurora
dashforge.generate(..., theme="./corporate.json")    # your Power BI theme JSON, applied as-is
```

## How it works

```
source ──introspect──▶ canonical schema ──▶ design brain ──▶ layout ──▶ Power BI project
        (+cardinality)   (types, counts)     (charts+filters)  (sidebar)   (PBIP + PBIR + TMDL)
                                                   ▲
                                            optional LLM refine
```

The output is a standard **PBIP** project (`.Report` in PBIR format + `.SemanticModel` in TMDL) that
opens directly in Power BI Desktop. The design brain, layout packer and emitter are cleanly
separated, so you can extend any one of them on its own.

## Documentation

- [Sources](docs/sources.md) — every connector, its config, and its credentials
- [Models](docs/models.md) — deterministic vs. LLM, and how to bring your own
- [Themes](docs/themes.md) — built-ins and using your corporate theme
- [Publishing](docs/publishing.md) — how this package is built and released

## Requirements

- Python 3.10+
- To open the generated project: Power BI Desktop with the **PBIR** ("Store reports using enhanced
  metadata format") preview enabled — see [docs/sources.md](docs/sources.md).

## License

MIT © Arka Gupta. See [LICENSE](LICENSE).
