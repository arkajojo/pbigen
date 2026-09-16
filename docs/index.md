---
hide:
  - navigation
  - toc
---

<div class="pbigen-hero" markdown>

![pbigen](https://raw.githubusercontent.com/arkajojo/pbigen/main/assets/logo.svg)

<div class="headline">World-class Power BI dashboards, generated from any data source.</div>

<div class="tagline">Point pbigen at a table. It reads the schema, reasons about the shape of the
data, and writes a clean, ready-to-open Power BI project — deterministically, or refined by any LLM.
Free, local, open source.</div>

<div class="cta" markdown>
[Get started](recipes.md){ .md-button .md-button--primary }
[Why pbigen?](why.md){ .md-button }
[Browse the recipes](recipes.md){ .md-button }
</div>

<div class="pills">16 data sources · deterministic or any LLM · MIT · no cloud capacity</div>

</div>

---

## Install

```bash
pip install pbigen                 # core (dependency-light)
pip install "pbigen[bigquery]"     # + one source driver: bigquery, snowflake, lakehouse, …
pip install "pbigen[llm]"          # + optional LLM-refined design
```

## 60 seconds, no cloud account

```bash
pip install "pbigen[lakehouse]" pyarrow
python -c "import pyarrow as pa,pyarrow.parquet as pq,random,datetime as d; r=random.Random(1); \
pq.write_table(pa.table({'order_date':[d.date(2024,1,1)+d.timedelta(days=r.randint(0,540)) for _ in range(500)],\
'region':[r.choice(['North','South','East','West']) for _ in range(500)],\
'status':[r.choice(['New','Shipped','Returned']) for _ in range(500)],\
'revenue':[round(r.uniform(50,5000),2) for _ in range(500)]}),'orders.parquet')"

pbigen generate --source parquet --set uri=orders.parquet \
  --objective "Sales overview by region and status over time" --theme midnight --out out
```

Open `out/Orders/Orders.pbip` in Power BI Desktop (enable the PBIR preview once — see
[Recipes → Open in Desktop](recipes.md#12-open-it-in-power-bi-desktop)).

---

## What you can do

<div class="grid cards" markdown>

- :material-database-search: **Connect anything**
  BigQuery/BigLake/Omni, Snowflake, Redshift, Synapse/Fabric, Databricks, ClickHouse, Postgres,
  Athena, a Parquet/Iceberg/Delta lake on GCS/S3/ADLS, or a Cube semantic layer.
  [Sources & auth →](sources.md)

- :material-brain: **Deterministic or LLM design**
  A reproducible, cardinality-aware engine by default (no key, no network); optionally let any LLM
  refine it — metadata only. [Deterministic vs LLM →](deterministic-vs-llm.md)

- :material-palette-swatch: **Match any house style**
  Built-in executive themes, bring-your-own theme JSON, a logo, left/right nav — or
  **extract the theme + logo from a shared `.pbix`** and pour your data into that shell.
  [Themes, logo & shell →](themes.md)

- :material-cog-play: **Controls that matter**
  Import vs DirectQuery, `row_limit` sampling for huge tables, and a clean Python API + CLI.
  [Recipes →](recipes.md)

- :material-shield-check: **Safe & portable**
  Read-only, metadata-only, standards-based **PBIP** output that validates against Microsoft's
  schemas and opens in Desktop. Version-control it like code.

- :material-flask: **Test everything**
  A self-serve verification harness — offline check, per-source, schema validation, and the full
  matrix. [Testing →](testing.md)

</div>

---

## Why not just use Copilot or an agentic BI tool?

Most AI dashboard tools are **cloud services that build inside their own surface** and cost per seat
or per capacity. pbigen is a **small open-source library** that produces **portable Power BI files you
own**, on your machine, for free — deterministically if you want, with **no data leaving your
environment**. See the full breakdown: [**Why pbigen →**](why.md)

---

MIT © Arka Gupta · [GitHub](https://github.com/arkajojo/pbigen) · [PyPI](https://pypi.org/project/pbigen/)
