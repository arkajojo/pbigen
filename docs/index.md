<p align="center">
  <img src="https://raw.githubusercontent.com/arkajojo/pbigen/main/assets/logo.svg" alt="pbigen" width="420">
</p>

# pbigen — Power BI dashboards from any data source

**pbigen** points at a table or view, reads its schema, reasons about the *shape* of the data (types
and cardinality), and writes a ready-to-open Power BI project — a navigation sidebar with your brand
and filters, KPI cards, data-appropriate charts, a detail table, and usage notes — laid out cleanly,
every time. No hand-built templates, no copy-pasting M queries.

The output is a standard, version-controllable **PBIP** project (PBIR report + TMDL semantic model)
that opens directly in Power BI Desktop.

## Install

```bash
pip install pbigen                 # core
pip install "pbigen[bigquery]"     # + a source driver (bigquery, snowflake, lakehouse, …)
pip install "pbigen[llm]"          # + optional LLM-refined design
```

## 60-second start

```bash
# offline, no cloud account — build a sample file and generate from it
pip install "pbigen[lakehouse]" pyarrow
python -c "import pyarrow as pa,pyarrow.parquet as pq,random,datetime as d; r=random.Random(1); \
pq.write_table(pa.table({'order_date':[d.date(2024,1,1)+d.timedelta(days=r.randint(0,540)) for _ in range(500)],\
'region':[r.choice(['N','S','E','W']) for _ in range(500)],'revenue':[round(r.uniform(50,5000),2) for _ in range(500)]}),'orders.parquet')"
pbigen generate --source parquet --set uri=orders.parquet --objective "Sales overview" --theme midnight --out out
```
Then open `out/Orders/Orders.pbip` in Power BI Desktop (enable the PBIR preview once — see
[Recipes](recipes.md#12-open-it-in-power-bi-desktop)).

## Where to go next

<div class="grid cards" markdown>

- :material-book-open-variant: **[Recipes (cookbook)](recipes.md)** — copy-paste examples for every
  feature: any warehouse, sampling, custom theme, logo + nav, replicate a `.pbix` shell, DirectQuery,
  any LLM, local model, Python API. **Start here to build.**
- :material-database: **[Sources & authentication](sources.md)** — every connector: install,
  authenticate (credentials + IAM), configure, test.
- :material-robot: **[Models](models.md)** — deterministic by default; any LLM (OpenAI, Anthropic,
  Gemini, Azure, Bedrock, local Ollama) with env-var auth.
- :material-palette: **[Themes, logo & shell](themes.md)** — built-ins, bring-your-own theme,
  `sidebarColor`/`accentColor`, logo, nav side, and replicating a shared report's shell.
- :material-check-decagram: **[Testing](testing.md)** — the self-serve verification harness.
- :material-package-variant: **[Publishing](publishing.md)** — the maintainer/release runbook.

</div>

## What makes it different

- **Portable & free** — native Power BI files you own, generated locally or in CI. No Fabric capacity,
  no SaaS, no lock-in.
- **Metadata-only & safe** — sources are read-only and introspection-only; no rows are read to design
  the report (and only metadata is ever sent to an optional LLM).
- **Deterministic by default** — reproducible, cardinality-aware design with **no key and no network**;
  an LLM is optional.

MIT-licensed · [GitHub](https://github.com/arkajojo/pbigen) · [PyPI](https://pypi.org/project/pbigen/)
