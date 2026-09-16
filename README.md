<p align="center">
  <img src="https://raw.githubusercontent.com/arkajojo/pbigen/main/assets/logo.svg" alt="pbigen" width="440">
</p>

<h3 align="center">Generate world-class Power BI dashboards from any data source — automatically.</h3>

<p align="center">
  <a href="https://pypi.org/project/pbigen/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pbigen.svg?color=4C6FFF"></a>
  <a href="https://pypi.org/project/pbigen/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/pbigen.svg?color=22C1C3"></a>
  <a href="https://github.com/arkajojo/pbigen/actions"><img alt="CI" src="https://github.com/arkajojo/pbigen/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-1B1F3B.svg"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-beta-FDBB2D.svg">
</p>

---

Point **pbigen** at a table or view. It reads the schema, reasons about the *shape* of the data
(types and cardinality), and writes a ready-to-open Power BI project: a left navigation sidebar with
your brand and filters, KPI cards, data-appropriate charts, a detail table, and a "how to use this
report" note — laid out cleanly, every time.

No hand-built templates. No copy-pasting M queries. No guessing which chart fits which column.

```python
import pbigen

result = pbigen.generate(
    "bigquery",
    source_config={"project": "my-proj", "dataset": "sales", "table": "orders"},
    objective="Revenue and orders by region over time",
    theme="midnight",
    out_dir="out",
)
print(result.pbip_path)   # open this in Power BI Desktop
```

<br>

## Table of contents

- [Why pbigen](#why-pbigen)
- [How pbigen compares](#how-pbigen-compares)
- [Features](#features)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Supported sources](#supported-sources)
- [Models: deterministic by default, LLM optional](#models-deterministic-by-default-llm-optional)
- [Themes: bring your own, or use a built-in](#themes-bring-your-own-or-use-a-built-in)
- [Layout, logo & storage mode](#layout-logo--storage-mode)
- [Replicate a report's design shell](#replicate-a-reports-design-shell)
- [How it works](#how-it-works)
- [Anatomy of the output](#anatomy-of-the-output)
- [Opening the result in Power BI Desktop](#opening-the-result-in-power-bi-desktop)
- [The design intelligence](#the-design-intelligence)
- [Python API](#python-api)
- [Command-line interface](#command-line-interface)
- [Extending pbigen](#extending-pbigen)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

<br>

## Why pbigen

Building a good Power BI report by hand is slow and inconsistent. Someone picks the charts, wires
every field, styles every visual, writes the connection query, and repeats it for the next dataset.
The mechanical 90% eats the time that should go to the 10% that actually needs judgement.

pbigen does the mechanical 90% correctly and consistently. It is **opinionated about good
defaults** and **unopinionated about your stack**:

- **Opinionated defaults** — cardinality-aware chart selection, a date column becomes a range filter
  (never a 500-row dropdown), wide breakdowns go in a matrix, KPIs lead every page, and a clean
  navigation sidebar is always there.
- **Unopinionated stack** — bring your own warehouse or lakehouse, your own model (or none), and your
  own theme.

The output is a standard, version-controllable **PBIP** project — not a black-box binary — so it
drops straight into source control and your existing Power BI workflow.

<br>

## How pbigen compares

AI dashboard generation is a crowded space in 2026 — Power BI Copilot and Agent Skills, plus
agentic BI platforms like ThoughtSpot, Tableau Pulse, Sigma, Domo and Tellius. Most of them are
powerful, and most are **cloud services that build dashboards inside their own surface**. pbigen
takes a different shape: it's a small, open-source library that turns a table into **portable,
version-controlled Power BI files** on your machine — free, and offline by default.

| Capability | **pbigen** | Power BI Copilot / Agent Skills | Agentic BI platforms<br>(ThoughtSpot, Sigma, Tableau Pulse, Domo, Tellius) | Generic LLM<br>(ChatGPT / Claude) |
|---|:---:|:---:|:---:|:---:|
| Outputs **native, portable Power BI files** (PBIP you own) | ✅ | ⚠️ builds in the service | ❌ their own BI surface | ❌ snippets only |
| **Version-controlled, CI-friendly** text output (PBIR + TMDL) | ✅ | ⚠️ not the generation flow | ❌ | ❌ |
| Runs **locally / in CI**, no paid cloud capacity | ✅ | ❌ needs Fabric capacity (F2+) | ❌ SaaS subscription | ⚠️ needs API/subscription |
| Works with **no LLM / API key** (deterministic) | ✅ | ❌ | ❌ | ❌ |
| One interface across warehouses **+ lakehouse (Iceberg/Delta) + semantic layer**, multi-cloud | ✅ | ⚠️ Fabric / OneLake-centric | ⚠️ varies by vendor | ❌ |
| **Metadata-only** — no row data leaves your environment to design | ✅ | ⚠️ cloud service | ⚠️ SaaS | ❌ you paste data |
| **Open source (MIT)**, self-hostable, no lock-in | ✅ | ❌ | ❌ | ❌ |
| Cost | **Free** | Paid (Fabric capacity) | Paid (per-seat SaaS) | Usage-based |

*(⚠️ = partial or conditional; comparisons reflect each tool's common default in 2026, not every edge case. Copilot / Agent Skills and the agentic platforms are genuinely capable — pbigen is the open, local, file-first option, and pairs fine alongside them.)*

<br>

## Features

- 🔌 **16 source kinds, one interface** — warehouses, query engines, open table formats on every
  major cloud, and a semantic layer.
- 🧠 **Data-shape-aware design** — chart and filter choices follow from column types and cardinality,
  not guesswork.
- 🎨 **Executive aesthetics** — light canvas, raised white cards with coloured KPI accent bars, big
  numbers, refined typography and charts — with three polished built-in themes or your own theme JSON.
- 🏗️ **Reusable design shell** — put the nav sidebar left or right (`--nav`), add a logo (`--logo`),
  and **`extract-template`** the theme + logo out of a shared `.pbix` to regenerate *your* data in
  someone else's look.
- ⚙️ **Storage & scale controls** — `--mode import|directquery`, and `row_limit` to sample a huge
  table for fast iteration.
- 🤖 **Pluggable design model** — deterministic by default (no key, no network); optionally let any
  LiteLLM model (hosted or fully local) refine the design. **Only metadata is ever sent.**
- 🧱 **Standards-based output** — a PBIP project (PBIR report + TMDL semantic model) that validates
  against Microsoft's published schemas and opens directly in Power BI Desktop.
- 🔒 **Read-only and safe** — sources are introspection-only; no rows are read to design the report.
- 🧩 **Clean seams** — source → design → layout → emit are independent and individually testable.
- 🖥️ **Python API and CLI** — script it or run it from the terminal.

<br>

## Installation

```bash
pip install pbigen
```

The core is dependency-light. Install only the extras you need — each pulls in exactly one stack's
driver:

| Extra | Installs support for |
|-------|----------------------|
| `pbigen[bigquery]` | BigQuery, BigLake, BigQuery Omni |
| `pbigen[redshift]` | Amazon Redshift |
| `pbigen[athena]` | Amazon Athena |
| `pbigen[snowflake]` | Snowflake |
| `pbigen[synapse]` | Azure Synapse / Microsoft Fabric / SQL Server |
| `pbigen[databricks]` | Databricks SQL |
| `pbigen[clickhouse]` | ClickHouse |
| `pbigen[postgres]` | PostgreSQL |
| `pbigen[lakehouse]` | Parquet, Iceberg, Delta on local / GCS / S3 / ADLS (DuckDB) |
| `pbigen[cube]` | Cube semantic layer |
| `pbigen[llm]` | LLM-refined design via LiteLLM |
| `pbigen[all]` | Everything above |

```bash
pip install "pbigen[bigquery]"
pip install "pbigen[lakehouse,llm]"
pip install "pbigen[all]"
```

**Requirements:** Python 3.10+. To open the generated project you need Power BI Desktop with the
PBIR preview enabled — see [Opening the result](#opening-the-result-in-power-bi-desktop).

<br>

## Quickstart

### Python

```python
import pbigen

result = pbigen.generate(
    "snowflake",
    source_config={
        "account": "ab12345", "warehouse": "BI_WH",
        "database": "ANALYTICS", "schema": "SALES", "table": "ORDERS",
    },
    objective="Sales performance by region and product",
    theme="midnight",
    out_dir="out",
    name="SalesOverview",
)
print(f"{result.n_pages} pages, {result.n_columns} columns → {result.pbip_path}")
```

### Command line

```bash
pbigen generate --source snowflake \
  --set account=ab12345 warehouse=BI_WH database=ANALYTICS schema=SALES table=ORDERS \
  --objective "Sales performance by region and product" \
  --theme midnight --out out --name SalesOverview
```

### Try it offline in 30 seconds

No cloud account needed — generate from a local Parquet file:

```bash
pip install "pbigen[lakehouse]" pyarrow
python examples/generate_from_parquet.py     # builds a sample file and generates from it
```

> **Testing it for real?** **[docs/testing.md](https://github.com/arkajojo/pbigen/blob/main/docs/testing.md)** is a self-serve guide for your whole
> team: how to install, **authenticate**, and verify every source and model — from the 30-second
> offline check to a full BigQuery matrix (deterministic × LLM, built-in × custom theme) validated
> against Microsoft's schemas.

<br>

## Supported sources

Every adapter implements the same read-only contract — **introspect** (columns + canonical types),
**approx_distinct** (cardinality, to drive design), and **power_query** (the M the report uses to
connect at refresh). Per-source **authentication**, config, and a test recipe live in
**[docs/sources.md](https://github.com/arkajojo/pbigen/blob/main/docs/sources.md)**; the end-to-end verification guide is **[docs/testing.md](https://github.com/arkajojo/pbigen/blob/main/docs/testing.md)**.

| Cloud / family | Sources | Extra |
|----------------|---------|-------|
| **GCP** | BigQuery, BigLake, BigQuery Omni; Parquet / Iceberg / Delta in GCS | `bigquery`, `lakehouse` |
| **AWS** | Redshift, Athena; Parquet / Iceberg / Delta in S3 | `redshift`, `athena`, `lakehouse` |
| **Azure** | Synapse, Fabric (SQL endpoint); Parquet / Iceberg / Delta in ADLS | `synapse`, `lakehouse` |
| **Multi / other** | Snowflake, Databricks, ClickHouse, PostgreSQL | `snowflake`, `databricks`, `clickhouse`, `postgres` |
| **Semantic layer** | Cube | `cube` |

```bash
pbigen sources                                   # list every source kind
pbigen test --source lakehouse --set uri=./sales.parquet fmt=parquet   # verify connectivity
```

Open table formats (Parquet, Apache Iceberg, Delta Lake) are read on local disk or any of the three
clouds through a single DuckDB-powered adapter — no cluster required for introspection. For *report
refresh*, raw Parquet is reachable via Power BI's storage connectors; Iceberg/Delta are best served
through a Fabric Lakehouse or Databricks SQL endpoint (details in [docs/sources.md](https://github.com/arkajojo/pbigen/blob/main/docs/sources.md)).

<br>

## Models: deterministic by default, LLM optional

Out of the box, pbigen designs dashboards with a **deterministic, no-key engine** — no network
call, no cost, fully reproducible. To let a language model refine the design, pass any
[LiteLLM](https://github.com/BerriAI/litellm) model id — hosted or a local open-source model:

```python
pbigen.generate("bigquery", source_config={...},
                   model="gpt-4o-mini")                     # bring your own key via env

pbigen.generate("bigquery", source_config={...},
                   model="anthropic/claude-sonnet-4-6")

pbigen.generate("bigquery", source_config={...},
                   model="ollama/llama3",                   # fully local, open-source
                   model_config={"api_base": "http://localhost:11434"})
```

> **Privacy:** only **metadata** — column names, canonical types and approximate distinct counts —
> is ever sent to a model. No row data leaves your machine. Every field the model returns is
> validated against the live schema, and if the model is unreachable or returns something unusable,
> pbigen falls back to the deterministic design so generation never hard-fails.

More in **[docs/models.md](https://github.com/arkajojo/pbigen/blob/main/docs/models.md)**.

<br>

## Themes: bring your own, or use a built-in

```python
pbigen.generate(..., theme="midnight")            # built-in: midnight | slate | aurora
pbigen.generate(..., theme="./corporate.json")    # your Power BI theme JSON, applied as-is
```

| Theme | Look |
|-------|------|
| `midnight` | Deep indigo sidebar, blue/teal data colours |
| `slate` | Neutral slate, red accent |
| `aurora` | Deep green sidebar, green/blue data colours |

Your theme travels with the project as a registered custom theme. More in
**[docs/themes.md](https://github.com/arkajojo/pbigen/blob/main/docs/themes.md)**.

<br>

## Layout, logo & storage mode

```bash
pbigen generate ... --nav right                 # navigation sidebar on the right (default: left)
pbigen generate ... --logo ./assets/logo.png    # drop a logo image into the nav sidebar
pbigen generate ... --mode directquery          # live queries instead of an imported copy (import is default)
pbigen generate --source bigquery --set ... row_limit=50000   # sample a huge table for fast iteration
```

- **`--nav left|right`** mirrors the whole shell (sidebar, filters, logo, notes) to that side.
- **`--logo`** copies the image into the report's registered resources and binds it as an image visual.
- **`--mode`** sets the semantic-model storage mode (`import` loads a copy; `directquery` queries the
  source live — needs a DirectQuery-capable source such as a warehouse).
- **`row_limit`** (BigQuery `--set`) generates a `Table.FirstN(…, N)` sample so big tables build fast.

## Replicate a report's design shell

Have a report you like — say a colleague shares its `.pbix`? Reuse its **look** (theme, colours,
fonts, logo, nav layout) and pour **your own data** into it. A Power BI *theme* only carries
colours/fonts/visual-style defaults — the rest of the shell you match with `--nav`/`--logo`.

```bash
# 1) pull the reusable shell out of the shared .pbix
pbigen extract-template their_report.pbix --out template
#    → template/theme.json          (their custom theme, if any)
#    → template/assets/<logo>.png   (their logo / background images)

# 2) regenerate YOUR data into that shell
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --theme template/theme.json --logo template/assets/<logo>.png --nav right --out out
```

**What is and isn't replicated:** the **theme + logo + nav layout** are matched apple-to-apple; the
**visuals and data are yours** (that's the point — your charts, not theirs). If the shared report used
only a built-in theme, there's no custom `theme.json` to extract — `--nav`/`--logo` and a gallery
theme still let you match the shell. For an *exact* clone of the same report on the same data, Power
BI Desktop's native **File → Save as → `.pbip`** is the right tool — pbigen reuses the shell, it
doesn't clone a specific report.

<br>

## How it works

```
 source ──introspect──▶ canonical schema ──▶ design brain ──▶ layout ──▶ Power BI project
         (+cardinality)   (types, counts)     (charts+filters)  (sidebar)   (PBIP + PBIR + TMDL)
                                                     ▲
                                              optional LLM refine
                                              (metadata only)
```

1. **Source** introspects the table (metadata only) and reports approximate cardinality.
2. **Design brain** classifies every column (measure / date / category / geo / id), proposes
   measures, and picks visuals and filters from the data shape. An LLM can refine this; the rules
   always produce a complete design on their own.
3. **Layout** packs the page — a left sidebar for brand + filters + notes, a KPI row, then charts
   and tables placed by footprint.
4. **Emitter** writes a standard PBIP project: a PBIR report and a TMDL semantic model wired to the
   source via Power Query.

<br>

## Anatomy of the output

```
out/SalesOverview/
├── SalesOverview.pbip                       # open this in Power BI Desktop
├── SalesOverview.Report/                    # the report (PBIR format)
│   ├── definition.pbir
│   └── definition/
│       ├── report.json                      # theme + layout settings
│       ├── version.json
│       ├── pages/
│       │   ├── pages.json                    # page order
│       │   └── <page>/page.json + visuals/<v>/visual.json
│       └── StaticResources/RegisteredResources/<theme>.json
└── SalesOverview.SemanticModel/             # the model (TMDL)
    ├── definition.pbism
    └── definition/
        ├── database.tmdl
        ├── model.tmdl
        └── tables/<table>.tmdl               # columns, DAX measures, the M connection
```

Everything is text and version-control-friendly. The report JSON validates against Microsoft's
published PBIR JSON schemas.

<br>

## Opening the result in Power BI Desktop

The output is a **PBIP** project. Enable the enhanced report format once:

1. **File → Options and settings → Options → Preview features**
2. Tick **"Store reports using enhanced metadata format (PBIR)"**
3. Restart Power BI Desktop.

Then open the `.pbip` file and **Refresh** to load data through the generated connection. (This is a
one-time setting; PBIR is Microsoft's text-based report format that pbigen emits.)

<br>

## The design intelligence

The deterministic engine makes these calls from the data shape, before any LLM is involved:

- **Column roles** — measures, dates, categories, geo and identifiers are detected from type and
  name, so ids and codes never get charted as if they were metrics.
- **Dates are ranges, not dropdowns** — a real date/time column drives a range slider; a 500-value
  dropdown never happens.
- **Donut vs. bar** — a breakdown with ≤ 8 categories becomes a donut, otherwise a bar.
- **Redundant filters dropped** — once a real date exists, derived period columns (year, month,
  `year_month`) are kept out of the filter rail.
- **Wide goes wide** — matrices with a series or many measures, and wide tables, get full width;
  narrow visuals pair up two-across.
- **A narrative** — pages flow Executive Summary → Trends → Segmentation → Detail, each led by KPI
  cards, with a "how to use this report" note in the sidebar.

<br>

## Python API

```python
pbigen.generate(
    source,                    # a source kind string, or a configured Source instance
    *,
    out_dir="out",             # where to write the project
    name=None,                 # project name (defaults to the table's display name)
    objective="",              # plain-language description of what the report should answer
    model=None,                # None/"deterministic" | LiteLLM model id | a Model instance
    theme=None,                # built-in name | path to a Power BI theme JSON
    mode="import",             # "import" or "directquery" (semantic-model storage mode)
    nav="left",                # navigation sidebar side: "left" or "right"
    logo=None,                 # path to a logo image to place in the nav sidebar
    source_config=None,        # dict passed to the source adapter (when source is a string)
    model_config=None,         # dict passed to the model (e.g. api_key, api_base, temperature)
) -> GenerateResult
```

```python
@dataclass
class GenerateResult:
    pbip_path: str       # path to the .pbip to open
    design: Design       # the pages/visuals/measures that were generated
    table: str
    n_columns: int
    n_pages: int
    model_name: str      # "deterministic" or e.g. "litellm:gpt-4o-mini"
```

Helpers: `pbigen.available_kinds()`, `pbigen.available_themes()`, `pbigen.get_source(kind, **cfg)`.

<br>

## Command-line interface

```bash
pbigen generate --source <kind> [--set k=v ...] [--objective ...] [--model ...] [--theme ...] \
                   [--mode import|directquery] [--nav left|right] [--logo IMG] [--out DIR] [--name NAME]
pbigen extract-template <file.pbix> [--out DIR]    # reuse a shared report's theme + logo + shell
pbigen test     --source <kind> [--set k=v ...]      # verify connectivity + introspection
pbigen sources                                       # list available source kinds
pbigen themes                                        # list built-in themes
pbigen --version
```

`--set` takes `key=value` pairs forwarded to the adapter; integers and booleans are coerced.

<br>

## Extending pbigen

**Add a source** — subclass `Source` (or `SqlSource` for a SQLAlchemy dialect), implement
`introspect`, `approx_distinct` and `power_query`, and register it:

```python
from pbigen.sources.base import Source

class MySource(Source):
    kind = "mysource"
    def introspect(self): ...
    def approx_distinct(self, columns): ...
    def power_query(self): ...
```

**Add a design model** — subclass `Model` and return a `Design` (start from the deterministic one):

```python
from pbigen.models.base import Model
from pbigen.core.design import design as deterministic

class MyModel(Model):
    name = "my-model"
    def design(self, schema, objective):
        return deterministic(schema, objective)   # then refine

pbigen.generate(..., model=MyModel())
```

See [CONTRIBUTING.md](https://github.com/arkajojo/pbigen/blob/main/CONTRIBUTING.md) for the full guide.

<br>

## Documentation

| Guide | What's in it |
|-------|--------------|
| **[docs/recipes.md](https://github.com/arkajojo/pbigen/blob/main/docs/recipes.md)** | Copy-paste end-to-end recipes for **every** feature: offline, any warehouse, sampling, custom theme, logo + nav, replicate a `.pbix` shell, DirectQuery, LLM (any provider), local model, Python API, schema-check, open in Desktop. **Start here to build.** |
| **[docs/testing.md](https://github.com/arkajojo/pbigen/blob/main/docs/testing.md)** | Self-serve verification for every source and model — offline check → universal 6-step → schema validation → the full BigQuery matrix → troubleshooting. **Start here to test.** |
| **[docs/sources.md](https://github.com/arkajojo/pbigen/blob/main/docs/sources.md)** | Every connector: install, **authenticate** (with how to get credentials + IAM), configure, test, generate. |
| **[docs/models.md](https://github.com/arkajojo/pbigen/blob/main/docs/models.md)** | Use any LLM: provider matrix (OpenAI, Anthropic, Gemini, Azure, Bedrock, local Ollama/vLLM) with env-var auth + examples. |
| **[docs/themes.md](https://github.com/arkajojo/pbigen/blob/main/docs/themes.md)** | Built-in themes and bringing your own Power BI theme JSON. |
| **[docs/publishing.md](https://github.com/arkajojo/pbigen/blob/main/docs/publishing.md)** | Maintainer runbook: build, release to PyPI, and the tag-triggered Trusted-Publishing workflow. |
| **[examples/](https://github.com/arkajojo/pbigen/tree/main/examples)** | Runnable scripts: local Parquet, BigQuery, LLM-refined design, and the 4-combo BigQuery verification harness. |
| **[CONTRIBUTING.md](https://github.com/arkajojo/pbigen/blob/main/CONTRIBUTING.md)** · **[CHANGELOG.md](https://github.com/arkajojo/pbigen/blob/main/CHANGELOG.md)** | How to contribute; release history. |

<br>

## Roadmap

- Live smoke-test matrix across every credentialed connector
- Refresh-friendly adapters for Iceberg/Delta via Fabric Lakehouse shortcuts
- Refactor mode: add pages / visuals to an existing report
- Additional emit targets beyond Power BI
- Relationship and multi-table (star-schema) modelling

Ideas and issues welcome — see [Contributing](#contributing).

<br>

## FAQ

**Does it read my data?** No. Sources introspect *metadata only* to design the report. Data is
loaded by Power BI at refresh time, on your machine, through the generated connection.

**Do I need an API key or an LLM?** No. The default design engine is deterministic and offline. An
LLM is entirely optional.

**What exactly gets sent to an LLM if I enable one?** Only column names, canonical types and
approximate distinct counts — never rows.

**Can I use my company's Power BI theme?** Yes — pass the path to your theme JSON as `theme=`.

**Why PBIP/PBIR?** It's Microsoft's text-based, source-control-friendly report format, so the output
is diffable, reviewable and CI-friendly rather than an opaque binary.

<br>

## Contributing

Contributions are very welcome. Set up a dev environment, run `ruff` and `pytest` (the suite runs
fully offline), and open a focused PR. See **[CONTRIBUTING.md](https://github.com/arkajojo/pbigen/blob/main/CONTRIBUTING.md)**.

<br>

## License

MIT © [Arka Gupta](https://github.com/arkajojo/pbigen/blob/main/AUTHORS.md). See [LICENSE](https://github.com/arkajojo/pbigen/blob/main/LICENSE).

<p align="center"><sub>Built by Arka Gupta.</sub></p>
