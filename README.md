<p align="center">
  <img src="https://raw.githubusercontent.com/arkajojo/dashforge/main/assets/logo.svg" alt="dashforge" width="440">
</p>

<h3 align="center">Generate world-class Power BI dashboards from any data source — automatically.</h3>

<p align="center">
  <a href="https://pypi.org/project/dashforge/"><img alt="PyPI" src="https://img.shields.io/pypi/v/dashforge.svg?color=4C6FFF"></a>
  <a href="https://pypi.org/project/dashforge/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/dashforge.svg?color=22C1C3"></a>
  <a href="https://github.com/arkajojo/dashforge/actions"><img alt="CI" src="https://github.com/arkajojo/dashforge/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-1B1F3B.svg"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-beta-FDBB2D.svg">
</p>

---

Point **dashforge** at a table or view. It reads the schema, reasons about the *shape* of the data
(types and cardinality), and writes a ready-to-open Power BI project: a left navigation sidebar with
your brand and filters, KPI cards, data-appropriate charts, a detail table, and a "how to use this
report" note — laid out cleanly, every time.

No hand-built templates. No copy-pasting M queries. No guessing which chart fits which column.

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

<br>

## Table of contents

- [Why dashforge](#why-dashforge)
- [How dashforge compares](#how-dashforge-compares)
- [Features](#features)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Supported sources](#supported-sources)
- [Models: deterministic by default, LLM optional](#models-deterministic-by-default-llm-optional)
- [Themes: bring your own, or use a built-in](#themes-bring-your-own-or-use-a-built-in)
- [How it works](#how-it-works)
- [Anatomy of the output](#anatomy-of-the-output)
- [Opening the result in Power BI Desktop](#opening-the-result-in-power-bi-desktop)
- [The design intelligence](#the-design-intelligence)
- [Python API](#python-api)
- [Command-line interface](#command-line-interface)
- [Extending dashforge](#extending-dashforge)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

<br>

## Why dashforge

Building a good Power BI report by hand is slow and inconsistent. Someone picks the charts, wires
every field, styles every visual, writes the connection query, and repeats it for the next dataset.
The mechanical 90% eats the time that should go to the 10% that actually needs judgement.

dashforge does the mechanical 90% correctly and consistently. It is **opinionated about good
defaults** and **unopinionated about your stack**:

- **Opinionated defaults** — cardinality-aware chart selection, a date column becomes a range filter
  (never a 500-row dropdown), wide breakdowns go in a matrix, KPIs lead every page, and a clean
  navigation sidebar is always there.
- **Unopinionated stack** — bring your own warehouse or lakehouse, your own model (or none), and your
  own theme.

The output is a standard, version-controllable **PBIP** project — not a black-box binary — so it
drops straight into source control and your existing Power BI workflow.

<br>

## How dashforge compares

There are plenty of ways to make a dashboard. Almost none of them **auto-design a complete,
governed Power BI report from an arbitrary source and hand you version-controlled files.** That gap
is the point of dashforge.

| | **dashforge** | Power BI by hand | Power BI Copilot (Fabric) | Dashboard-as-code<br>(Looker / Evidence / Streamlit) |
|---|:---:|:---:|:---:|:---:|
| Auto-designs the whole report from a table | ✅ | ❌ | ⚠️ assists, still manual | ⚠️ you write it |
| One interface across warehouses **+ lakehouse + semantic layer**, multi-cloud | ✅ | ⚠️ manual per connector | ⚠️ Fabric-centric | ⚠️ varies |
| Emits **native** Power BI that opens in Desktop | ✅ | ✅ | ✅ | ❌ different tool / web app |
| Output is **text, version-controlled, CI-friendly** | ✅ | ⚠️ only if PBIR enabled | ❌ lives in the service | ✅ |
| Runs **locally / in CI**, no proprietary capacity | ✅ | ✅ (Desktop) | ❌ needs Fabric capacity | ✅ |
| Works with **no LLM / API key** (deterministic) | ✅ | ✅ | ❌ requires their AI | ✅ |
| **Metadata-only** — no row data leaves your machine to design | ✅ | ✅ | ⚠️ cloud service | ✅ |
| **Open source, MIT, no lock-in** | ✅ | ❌ | ❌ | ⚠️ mixed |

*(⚠️ = partial or conditional. Comparisons reflect the common default of each approach, not every edge case.)*

### The moat — why this is hard to copy

- **Correct, schema-valid PBIP/PBIR/TMDL emission is genuinely difficult.** Power BI's enhanced
  report format is strict and sparsely documented. dashforge's output validates against Microsoft's
  *published* JSON schemas — every generated report file, every run — so projects open in Desktop
  without repair. That correctness is earned, not trivial to reproduce.
- **A real design brain, not just a prompt.** The chart/filter choices come from a deterministic,
  cardinality-aware engine (column-role classification, donut-vs-bar thresholds, date-as-range,
  redundant-filter pruning, footprint-based layout). It's reproducible and free, with an LLM as an
  *optional* refiner — not a dependency.
- **Breadth behind one contract.** 16 source kinds across GCP, AWS, Azure, plus open table formats
  and a semantic layer, all behind the same `introspect → cardinality → connect` interface. Adding
  the next source is a small, isolated adapter.
- **Enterprise-safe by construction.** Read-only, metadata-only, runs on your machine or in CI, no
  cloud capacity to buy, no data egress to a vendor. That posture is easy to adopt and hard for a
  SaaS-locked tool to match.
- **Portable and composable.** MIT-licensed, clean seams (source / design / layout / emit), and
  text output that lives in git — so it compounds with your existing workflow instead of replacing it.

Where the moat **widens over time**: community source adapters, a theme/template ecosystem, and
additional emit targets — each addition benefits every user and raises the cost of catching up.

<br>

## Features

- 🔌 **16 source kinds, one interface** — warehouses, query engines, open table formats on every
  major cloud, and a semantic layer.
- 🧠 **Data-shape-aware design** — chart and filter choices follow from column types and cardinality,
  not guesswork.
- 🎨 **Themes** — three polished built-ins, or drop in your corporate Power BI theme JSON.
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
pip install dashforge
```

The core is dependency-light. Install only the extras you need — each pulls in exactly one stack's
driver:

| Extra | Installs support for |
|-------|----------------------|
| `dashforge[bigquery]` | BigQuery, BigLake, BigQuery Omni |
| `dashforge[redshift]` | Amazon Redshift |
| `dashforge[athena]` | Amazon Athena |
| `dashforge[snowflake]` | Snowflake |
| `dashforge[synapse]` | Azure Synapse / Microsoft Fabric / SQL Server |
| `dashforge[databricks]` | Databricks SQL |
| `dashforge[clickhouse]` | ClickHouse |
| `dashforge[postgres]` | PostgreSQL |
| `dashforge[lakehouse]` | Parquet, Iceberg, Delta on local / GCS / S3 / ADLS (DuckDB) |
| `dashforge[cube]` | Cube semantic layer |
| `dashforge[llm]` | LLM-refined design via LiteLLM |
| `dashforge[all]` | Everything above |

```bash
pip install "dashforge[bigquery]"
pip install "dashforge[lakehouse,llm]"
pip install "dashforge[all]"
```

**Requirements:** Python 3.10+. To open the generated project you need Power BI Desktop with the
PBIR preview enabled — see [Opening the result](#opening-the-result-in-power-bi-desktop).

<br>

## Quickstart

### Python

```python
import dashforge

result = dashforge.generate(
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
dashforge generate --source snowflake \
  --set account=ab12345 warehouse=BI_WH database=ANALYTICS schema=SALES table=ORDERS \
  --objective "Sales performance by region and product" \
  --theme midnight --out out --name SalesOverview
```

### Try it offline in 30 seconds

No cloud account needed — generate from a local Parquet file:

```bash
pip install "dashforge[lakehouse]" pyarrow
python examples/generate_from_parquet.py     # builds a sample file and generates from it
```

<br>

## Supported sources

Every adapter implements the same read-only contract — **introspect** (columns + canonical types),
**approx_distinct** (cardinality, to drive design), and **power_query** (the M the report uses to
connect at refresh). Full config and credentials for each live in **[docs/sources.md](docs/sources.md)**.

| Cloud / family | Sources | Extra |
|----------------|---------|-------|
| **GCP** | BigQuery, BigLake, BigQuery Omni; Parquet / Iceberg / Delta in GCS | `bigquery`, `lakehouse` |
| **AWS** | Redshift, Athena; Parquet / Iceberg / Delta in S3 | `redshift`, `athena`, `lakehouse` |
| **Azure** | Synapse, Fabric (SQL endpoint); Parquet / Iceberg / Delta in ADLS | `synapse`, `lakehouse` |
| **Multi / other** | Snowflake, Databricks, ClickHouse, PostgreSQL | `snowflake`, `databricks`, `clickhouse`, `postgres` |
| **Semantic layer** | Cube | `cube` |

```bash
dashforge sources                                   # list every source kind
dashforge test --source lakehouse --set uri=./sales.parquet fmt=parquet   # verify connectivity
```

Open table formats (Parquet, Apache Iceberg, Delta Lake) are read on local disk or any of the three
clouds through a single DuckDB-powered adapter — no cluster required for introspection. For *report
refresh*, raw Parquet is reachable via Power BI's storage connectors; Iceberg/Delta are best served
through a Fabric Lakehouse or Databricks SQL endpoint (details in [docs/sources.md](docs/sources.md)).

<br>

## Models: deterministic by default, LLM optional

Out of the box, dashforge designs dashboards with a **deterministic, no-key engine** — no network
call, no cost, fully reproducible. To let a language model refine the design, pass any
[LiteLLM](https://github.com/BerriAI/litellm) model id — hosted or a local open-source model:

```python
dashforge.generate("bigquery", source_config={...},
                   model="gpt-4o-mini")                     # bring your own key via env

dashforge.generate("bigquery", source_config={...},
                   model="anthropic/claude-sonnet-4-6")

dashforge.generate("bigquery", source_config={...},
                   model="ollama/llama3",                   # fully local, open-source
                   model_config={"api_base": "http://localhost:11434"})
```

> **Privacy:** only **metadata** — column names, canonical types and approximate distinct counts —
> is ever sent to a model. No row data leaves your machine. Every field the model returns is
> validated against the live schema, and if the model is unreachable or returns something unusable,
> dashforge falls back to the deterministic design so generation never hard-fails.

More in **[docs/models.md](docs/models.md)**.

<br>

## Themes: bring your own, or use a built-in

```python
dashforge.generate(..., theme="midnight")            # built-in: midnight | slate | aurora
dashforge.generate(..., theme="./corporate.json")    # your Power BI theme JSON, applied as-is
```

| Theme | Look |
|-------|------|
| `midnight` | Deep indigo sidebar, blue/teal data colours |
| `slate` | Neutral slate, red accent |
| `aurora` | Deep green sidebar, green/blue data colours |

Your theme travels with the project as a registered custom theme. More in
**[docs/themes.md](docs/themes.md)**.

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
one-time setting; PBIR is Microsoft's text-based report format that dashforge emits.)

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
dashforge.generate(
    source,                    # a source kind string, or a configured Source instance
    *,
    out_dir="out",             # where to write the project
    name=None,                 # project name (defaults to the table's display name)
    objective="",              # plain-language description of what the report should answer
    model=None,                # None/"deterministic" | LiteLLM model id | a Model instance
    theme=None,                # built-in name | path to a Power BI theme JSON
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

Helpers: `dashforge.available_kinds()`, `dashforge.available_themes()`, `dashforge.get_source(kind, **cfg)`.

<br>

## Command-line interface

```bash
dashforge generate --source <kind> [--set k=v ...] [--objective ...] \
                   [--model ...] [--theme ...] [--out DIR] [--name NAME]
dashforge test     --source <kind> [--set k=v ...]      # verify connectivity + introspection
dashforge sources                                       # list available source kinds
dashforge themes                                        # list built-in themes
dashforge --version
```

`--set` takes `key=value` pairs forwarded to the adapter; integers and booleans are coerced.

<br>

## Extending dashforge

**Add a source** — subclass `Source` (or `SqlSource` for a SQLAlchemy dialect), implement
`introspect`, `approx_distinct` and `power_query`, and register it:

```python
from dashforge.sources.base import Source

class MySource(Source):
    kind = "mysource"
    def introspect(self): ...
    def approx_distinct(self, columns): ...
    def power_query(self): ...
```

**Add a design model** — subclass `Model` and return a `Design` (start from the deterministic one):

```python
from dashforge.models.base import Model
from dashforge.core.design import design as deterministic

class MyModel(Model):
    name = "my-model"
    def design(self, schema, objective):
        return deterministic(schema, objective)   # then refine

dashforge.generate(..., model=MyModel())
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

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
fully offline), and open a focused PR. See **[CONTRIBUTING.md](CONTRIBUTING.md)**.

<br>

## License

MIT © [Arka Gupta](AUTHORS.md). See [LICENSE](LICENSE).

<p align="center"><sub>Built by Arka Gupta.</sub></p>
