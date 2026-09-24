<p align="center">
  <img src="https://raw.githubusercontent.com/arkajojo/pbigen/main/assets/logo.svg" alt="pbigen" width="440">
</p>

<h3 align="center">Your report's design. Your data's story. A finished Power BI dashboard — generated.</h3>

<p align="center">
  <a href="https://pypi.org/project/pbigen/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pbigen.svg?color=4C6FFF"></a>
  <a href="https://pypi.org/project/pbigen/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/pbigen.svg?color=22C1C3"></a>
  <a href="https://github.com/arkajojo/pbigen/actions"><img alt="CI" src="https://github.com/arkajojo/pbigen/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://arkajojo.github.io/pbigen/"><img alt="Docs" src="https://img.shields.io/badge/docs-arkajojo.github.io%2Fpbigen-7B5CFF.svg"></a>
  <a href="https://github.com/arkajojo/pbigen/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-1B1F3B.svg"></a>
</p>

---

**pbigen** turns a table into a complete, executive-grade Power BI report — and it can wear **the
design of a report you already have**.

1. **Download any `.pbix` you like** (your company's standard report, a colleague's, a gallery
   template). pbigen compiles it into a **template pack**: canvas, background, sidebar and header
   chrome, logo, title font, theme, and the formatting of every visual type — *none of its data*.
2. **Point pbigen at your data** (BigQuery, Snowflake, Databricks, Fabric, a Parquet/Iceberg/Delta
   lake … 16 sources). An AI design pipeline works like a senior BI consultant: it understands the
   **business context**, derives the **objectives and a KPI tree**, **researches** how leading
   companies in that domain measure it (live web search where your model supports it), writes a
   **storyboard**, then **critiques and repairs** its own design.
3. **Open the result in Power BI Desktop** — a structured story (summary → trends → drivers →
   detail → KPI definitions) laid into *your* design, with KPI cards that show green/red
   period-over-period change, ranked charts, monthly trends, and a `DESIGN.md` explaining every choice.

```bash
pip install "pbigen[bigquery,llm]"

pbigen template build company_standard.pbix --out brand_pack        # once

pbigen generate --source bigquery --set project=my-proj dataset=sales table=orders \
    --template brand_pack \
    --model gpt-4o --research web \
    --context "D2C retailer; leadership wants profitable growth and repeat customers"
```

No key? Drop `--model` — the deterministic engine still builds the full story offline, for free.

<br>

## Table of contents

- [Why pbigen](#why-pbigen)
- [How pbigen compares](#how-pbigen-compares)
- [What you get](#what-you-get)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Template packs: use any .pbix as the design](#template-packs-use-any-pbix-as-the-design)
- [The AI design pipeline](#the-ai-design-pipeline)
- [Supported sources](#supported-sources)
- [Models](#models)
- [Themes, logo, layout & storage mode](#themes-logo-layout--storage-mode)
- [How it works](#how-it-works)
- [Anatomy of the output](#anatomy-of-the-output)
- [Opening the result in Power BI Desktop](#opening-the-result-in-power-bi-desktop)
- [Python API](#python-api)
- [Command-line interface](#command-line-interface)
- [Extending pbigen](#extending-pbigen)
- [Documentation](#documentation)
- [FAQ](#faq)
- [Contributing](#contributing) · [License](#license)

<br>

## Why pbigen

Building a good Power BI report is two jobs, and both are slow:

- **Craft** — matching the house style: the canvas, the sidebar, the fonts, the card borders and
  shadows, the logo, repeated by hand for every new report.
- **Thinking** — deciding what the report is *for*: which KPIs matter, how they decompose, which
  question each page answers, which chart fits which question — so it tells a story instead of
  dumping "X by Y" charts.

pbigen automates both. The **template pack** takes the craft from a report you already like. The
**design pipeline** does the thinking the way a senior consultant would — and writes it down in a
`DESIGN.md` so the reasoning can be reviewed. The output is a standard **PBIP** project (PBIR +
TMDL): text files you own, diff, review and put in CI.

<br>

## How pbigen compares

| Capability | **pbigen** | Power BI Copilot / Agent Skills | Agentic BI platforms<br>(ThoughtSpot, Sigma, Tableau Pulse, Domo, Tellius) | Generic LLM<br>(ChatGPT / Claude) |
|---|:---:|:---:|:---:|:---:|
| Reuses **your existing report's design** (from a `.pbix`) | ✅ | ⚠️ themes only | ❌ | ❌ |
| Staged **business reasoning** (context → objectives → research → story → critique) | ✅ | ⚠️ | ⚠️ | ⚠️ ad hoc |
| Outputs **native, portable Power BI files** (PBIP you own) | ✅ | ⚠️ builds in the service | ❌ their own BI surface | ❌ snippets only |
| **Version-controlled, CI-friendly** text output (PBIR + TMDL) | ✅ | ⚠️ | ❌ | ❌ |
| Runs **locally / in CI**, no paid cloud capacity | ✅ | ❌ needs Fabric capacity | ❌ SaaS subscription | ⚠️ API/subscription |
| Works with **no LLM / API key** (deterministic) | ✅ | ❌ | ❌ | ❌ |
| One interface across warehouses **+ lakehouse + semantic layer**, multi-cloud | ✅ | ⚠️ Fabric-centric | ⚠️ varies | ❌ |
| **Metadata-only** by default — no row data sent to design | ✅ | ⚠️ cloud service | ⚠️ SaaS | ❌ you paste data |
| **Open source (MIT)**, no lock-in, free | ✅ | ❌ | ❌ | ❌ |

*(⚠️ = partial or conditional; comparisons reflect each tool's common default in 2026. Copilot and
the agentic platforms are genuinely capable — pbigen is the open, local, file-first option and pairs
fine alongside them.)*

<br>

## What you get

- 🎨 **Your design, reused** — `pbigen template build report.pbix` captures canvas size, page
  background, sidebar/header chrome, logo, title font, theme and per-visual formatting (borders,
  radius, shadows, slicer styling). New dashboards land in *their* content area, filter rail and header.
- 🧠 **A consultant-grade AI pipeline** — business context → objectives & KPI tree → research
  (live web search on OpenAI / Anthropic / Gemini, curated domain playbooks otherwise) → storyboard →
  self-critique & repair. Every field it returns is validated against the live schema.
- 📖 **A story, not a chart dump** — every page answers one headline question; every visual has a
  subtitle saying how to read it; an **About** page defines every KPI (formula, unit, direction).
- 📈 **Executive visuals** — KPI cards with a **coloured period-over-period delta** (red when cost
  goes up, green when revenue does), combo volume-vs-value charts, ranked bars, treemaps,
  waterfalls, scatter, scorecard matrices, **monthly** trends (never raw timestamps).
- 🧮 **Real KPI trees** — totals, distinct entities, ratios and KPI-on-KPI formulas
  (`Net Revenue = Gross − Discount`, `AOV = Revenue ÷ Orders`) emitted as clean DAX.
- 📝 **`DESIGN.md`** next to every report — the business context, objectives, KPI tree, research
  findings (with sources), storyline, critique changes and data gaps.
- 🔌 **16 source kinds, one interface** — BigQuery/BigLake/Omni, Snowflake, Redshift, Athena,
  Synapse/Fabric, Databricks, ClickHouse, Postgres, Parquet/Iceberg/Delta on local/GCS/S3/ADLS, Cube.
- 🔒 **Safe by design** — read-only introspection; only metadata goes to a model (aggregate
  profiles only if you opt in with `--profile`); output validates against Microsoft's PBIR schemas.
- 🆓 **Deterministic mode** — no key, no network: a complete story-structured dashboard offline.

<br>

## Installation

```bash
pip install pbigen                        # core (deterministic, offline)
pip install "pbigen[bigquery,llm]"        # + a source and the AI pipeline
pip install "pbigen[all]"                 # everything
```

| Extra | Installs support for |
|-------|----------------------|
| `pbigen[bigquery]` | BigQuery, BigLake, BigQuery Omni |
| `pbigen[redshift]` · `[athena]` | Amazon Redshift · Athena |
| `pbigen[snowflake]` | Snowflake |
| `pbigen[synapse]` | Azure Synapse / Microsoft Fabric / SQL Server |
| `pbigen[databricks]` · `[clickhouse]` · `[postgres]` | Databricks SQL · ClickHouse · PostgreSQL |
| `pbigen[lakehouse]` | Parquet, Iceberg, Delta on local / GCS / S3 / ADLS (DuckDB) |
| `pbigen[cube]` | Cube semantic layer |
| `pbigen[llm]` | The AI design pipeline via LiteLLM (any provider, hosted or local) |

**Requirements:** Python 3.10+, and Power BI Desktop with the PBIR preview enabled to open the output
([how](#opening-the-result-in-power-bi-desktop)). Check your setup any time with `pbigen doctor`.

<br>

## Quickstart

### 1. Try it offline in 30 seconds

```bash
pip install "pbigen[lakehouse]" pyarrow
python examples/generate_from_parquet.py      # builds a sample file and generates a full report
```

### 2. Your data, deterministic (no key)

```bash
pbigen generate --source snowflake \
  --set account=ab12345 warehouse=BI_WH database=ANALYTICS schema=SALES table=ORDERS \
  --objective "Sales performance by region and product" --out out
```

### 3. Your data, your design, AI-designed

```bash
export OPENAI_API_KEY=...                     # or ANTHROPIC_API_KEY / GEMINI_API_KEY / a local model
pbigen doctor --model gpt-4o                  # checks the key and whether web research is available

pbigen generate --source bigquery --set project=P dataset=D table=T \
  --template ~/Downloads/company_standard.pbix \
  --model gpt-4o --research web --profile \
  --context brief.md --audience "COO and regional managers" --out out
```

```text
pbigen ▸ 1/5 business context: ok (14.7s)
pbigen ▸ 2/5 objectives & KPI tree: ok (15.0s)
pbigen ▸ 3/5 research (web): ok (52.6s)
pbigen ▸ 4/5 storyboard & visual design: ok (39.2s)
pbigen ▸ 5/5 design critique & repair: ok (37.1s)
Generated 6 pages from orders (9 columns) using litellm:gpt-4o, in the template 'company_standard'.
Open:   out/Orders/Orders.pbip
Why:    out/Orders/DESIGN.md   (business context, KPI tree, storyline)
```

### Python

```python
import pbigen

result = pbigen.generate(
    "bigquery",
    source_config={"project": "my-proj", "dataset": "sales", "table": "orders"},
    template="brand_pack",                     # a pack folder, or a .pbix/.pbit/.pbip directly
    model="anthropic/claude-sonnet-4-5",       # omit for the deterministic engine
    research="web",
    context="D2C retailer; leadership wants profitable growth and repeat customers",
    out_dir="out",
)
print(result.pbip_path, result.design_md)
```

<br>

## Template packs: use any .pbix as the design

```bash
pbigen template build their_report.pbix --out brand_pack     # compile once
pbigen template show brand_pack                              # what it captured
pbigen generate --source ... --template brand_pack           # reuse for every new dashboard
pbigen generate --source ... --template their_report.pbix    # …or compile on the fly
```

```text
Template pack: company_standard  (from company_standard.pbix, reference page 'Overview')
  canvas      1920 x 1080
  content     x=340 y=150 w=1550 h=900
  header      x=340 y=24 w=1100 h=90  font=Segoe UI Semibold 28pt
  filters     x=24 y=180 w=280 h=640
  chrome      3 element(s): image, pageNavigator, shape
  background  yes
  styles      card, clusteredBarChart, donutChart, lineChart, pivotTable, slicer, tableEx, …
  theme       theme.json
  assets      2 image(s)
```

pbigen picks the report's richest page as the reference and measures it:

| Captured | How it is used |
|---|---|
| **Canvas** — page size, background image / wallpaper | every generated page uses the same canvas |
| **Content region** — where their data visuals live | your KPI band and story grid are laid out inside it |
| **Filter rail** — where their slicers live | your filters go there (stacked if tall, a band if wide) |
| **Header** — their most prominent title, its font/size/colour/alignment | your page title + headline question |
| **Chrome** — sidebar panels, header bands, logos, page navigators | copied with exact positions (tall panels grow with the page) |
| **Styles** — per visual type: borders, radius, shadows, title fonts, slicer look | applied under pbigen's bindings on every matching visual |
| **Theme** — their custom theme JSON + images | registered with the report (override with `--theme`) |

What is **not** copied: their data, field bindings, conditional formats tied to their fields, and
page-specific text — those are exactly what pbigen regenerates for your data. Reads legacy
`.pbix`/`.pbit` layouts and PBIR (`.pbip`/`.Report` folders or PBIR-format `.pbix`). A report pbigen
generated is itself a valid template. Details: **[docs/templates.md](https://github.com/arkajojo/pbigen/blob/main/docs/templates.md)**.

<br>

## The AI design pipeline

With `--model`, five expert stages run in sequence, each with its own persona, the curated design
knowledge base (IBCS, Few, Knaflic, Minto, plus domain KPI playbooks for mobility, commerce,
marketing, product, finance, operations, service, HR, SaaS and healthcare) and a strict JSON contract:

| Stage | Persona | Produces |
|---|---|---|
| 1. **Business context** | principal analytics consultant | domain, business model, grain, entities, audience & their decisions, column meanings, assumptions, caveats |
| 2. **Objectives & KPI tree** | head of strategy & analytics | north star, objectives → decisions → prioritised questions, 6-12 KPIs with exact formulas, unit and good direction, data **gaps** |
| 3. **Research** | BI research analyst | how leading organisations measure this domain, benchmarks, recommended views, pitfalls — **live web search** (`--research web`) or built-in playbooks |
| 4. **Storyboard** | IBCS-trained dashboard designer | 4-6 pages, a question per page, the right chart per question, subtitles, layout sizes, filters, coverage map |
| 5. **Critique & repair** | the most demanding reviewer | checks coverage, story flow, chart fitness, clarity, validity — returns the corrected design |

Then pbigen **validates everything against the live schema** — unknown columns dropped, donuts with
too many slices become ranked bars, trends move to the monthly grain, KPI-on-KPI formulas are
resolved — adds the period-over-period deltas and the About page, and writes `DESIGN.md`. If any
stage fails, the run continues; if no valid design emerges, the deterministic design is used and
the result says so.

**Privacy:** only metadata (column names, types, approximate distinct counts) is sent. `--profile`
adds aggregate profiles — min/max/avg, date ranges, top category values — never rows.

<br>

## Supported sources

Every adapter implements the same read-only contract — **introspect**, **approx_distinct**,
**profile** (opt-in aggregates) and **power_query** (the M the report refreshes with). Auth and
config per source: **[docs/sources.md](https://github.com/arkajojo/pbigen/blob/main/docs/sources.md)**.

| Cloud / family | Sources | Extra |
|----------------|---------|-------|
| **GCP** | BigQuery, BigLake, BigQuery Omni; Parquet / Iceberg / Delta in GCS | `bigquery`, `lakehouse` |
| **AWS** | Redshift, Athena; Parquet / Iceberg / Delta in S3 | `redshift`, `athena`, `lakehouse` |
| **Azure** | Synapse, Fabric (SQL endpoint); Parquet / Iceberg / Delta in ADLS | `synapse`, `lakehouse` |
| **Multi / other** | Snowflake, Databricks, ClickHouse, PostgreSQL | `snowflake`, `databricks`, `clickhouse`, `postgres` |
| **Semantic layer** | Cube | `cube` |

```bash
pbigen sources                                                      # list every source kind
pbigen test --source lakehouse --set uri=./sales.parquet fmt=parquet   # verify connectivity
```

<br>

## Models

```python
pbigen.generate(..., model=None)                              # deterministic (default): offline, free
pbigen.generate(..., model="gpt-4o")                          # OPENAI_API_KEY
pbigen.generate(..., model="anthropic/claude-sonnet-4-5")     # ANTHROPIC_API_KEY
pbigen.generate(..., model="gemini/gemini-2.5-flash")         # GEMINI_API_KEY
pbigen.generate(..., model="ollama/llama3.1",                 # fully local
                model_config={"api_base": "http://localhost:11434"})
```

Any [LiteLLM](https://github.com/BerriAI/litellm) model id works. Web research is used where the
provider supports it (OpenAI search models / GPT-5, Anthropic, Gemini); elsewhere `--research web`
falls back to the built-in knowledge automatically. Stronger models tell better stories — the
pipeline is written to get the most out of frontier models, and still validates small local ones.
More: **[docs/models.md](https://github.com/arkajojo/pbigen/blob/main/docs/models.md)**.

<br>

## Themes, logo, layout & storage mode

```bash
pbigen generate ... --theme midnight            # built-in: midnight | slate | aurora
pbigen generate ... --theme ./corporate.json    # your theme JSON (also overrides a template's theme)
pbigen generate ... --nav right --logo logo.png # pbigen shell: sidebar side + logo
pbigen generate ... --mode directquery          # live queries instead of an imported copy
pbigen generate ... --compare-days 7            # KPI deltas: last 7 days vs prior 7
pbigen generate --source bigquery --set ... row_limit=50000   # sample a huge table for fast iteration
```

<br>

## How it works

```
 your .pbix ──template build──▶ template pack (canvas · chrome · header · styles · theme)
                                                   │
 source ──introspect──▶ schema (+cardinality, +opt-in profile, +monthly grain)
                              │                    │
                              ▼                    ▼
        design: deterministic storyboard   or   AI pipeline (context → objectives →
                                                 research → storyboard → critique)
                              │
                              ▼
        finish: KPI-card deltas · About page · schema validation
                              │
                              ▼
        layout (12-col grid inside the frame) ──▶ PBIP project (PBIR + TMDL) + DESIGN.md
```

<br>

## Anatomy of the output

```
out/Orders/
├── Orders.pbip                             # open this in Power BI Desktop
├── DESIGN.md                               # the reasoning: context, KPI tree, research, storyline
├── Orders.Report/                          # the report (PBIR)
│   ├── definition.pbir
│   ├── StaticResources/RegisteredResources/   # theme, logo, template background & images
│   └── definition/
│       ├── report.json · version.json
│       └── pages/<page>/page.json + visuals/<v>/visual.json
└── Orders.SemanticModel/                   # the model (TMDL)
    └── definition/tables/<table>.tmdl      # columns, monthly grain, DAX measures, the M connection
```

<br>

## Opening the result in Power BI Desktop

1. **File → Options and settings → Options → Preview features** → tick **"Store reports using
   enhanced metadata format (PBIR)"** → restart (one time).
2. Keep the `.pbip`, `.Report` and `.SemanticModel` together (never open from inside a zip).
3. Open the `.pbip`, sign in to the source when prompted, and **Refresh**.

<br>

## Python API

```python
pbigen.generate(
    source,                    # a source kind string, or a configured Source instance
    *,
    template=None,             # template pack folder, or a .pbix/.pbit/.pbip to use as the design
    model=None,                # None/"deterministic" | LiteLLM model id | a Model instance
    objective="",              # what the dashboard should answer
    context="",                # business context: text, or a path to a brief/notes file
    audience="",               # who reads it
    research="builtin",        # "builtin" | "web" | "off"
    profile=False,             # send aggregate profiles (never rows) to the model
    critique=True,             # run the critique & repair stage
    compare_days=30,           # KPI card delta window
    theme=None,                # built-in name | theme JSON path (overrides a template's theme)
    mode="import",             # "import" | "directquery"
    nav="left", logo=None,     # pbigen shell options
    out_dir="out", name=None,
    source_config=None, model_config=None,
) -> GenerateResult            # pbip_path, design_md, design, template, n_pages, model_name, …

from pbigen.template import build_pack, load_pack   # compile / load template packs in code
```

<br>

## Command-line interface

```bash
pbigen generate --source <kind> [--set k=v ...] [--template PACK|FILE.pbix] [--model ID]
                [--objective TEXT] [--context TEXT|FILE] [--audience TEXT]
                [--research builtin|web|off] [--profile] [--no-critique] [--compare-days N]
                [--theme NAME|FILE] [--mode import|directquery] [--nav left|right] [--logo IMG]
                [--out DIR] [--name NAME]
pbigen template build <report.pbix|.pbit|.pbip> [--out DIR] [--page NAME] [--name NAME]
pbigen template show  <pack>
pbigen doctor [--model ID]          # installed extras, model key, web-research availability
pbigen test   --source <kind> [--set k=v ...]
pbigen sources | themes | --version
```

<br>

## Extending pbigen

**Add a source** — subclass `Source` (or `SqlSource`), implement `introspect`, `approx_distinct`,
`power_query` (and optionally `profile`), and register it in `pbigen.sources`.

**Add a design model** — subclass `Model` and return a `Design`; reuse the pipeline with your own
transport if you like:

```python
from pbigen.ai.pipeline import DesignPipeline, DesignRequest
from pbigen.models.base import Model

class MyModel(Model):
    name = "my-model"
    def design(self, schema, objective, request=None):
        complete = lambda system, user, web=False: my_llm(system, user)   # -> JSON text
        return DesignPipeline(complete, self.name).run(schema, request or DesignRequest(objective))
```

**Add a domain playbook** — append a `Playbook` in `pbigen/ai/knowledge.py` (keywords, north star,
objectives, KPIs, storyline, pitfalls). See [CONTRIBUTING.md](https://github.com/arkajojo/pbigen/blob/main/CONTRIBUTING.md).

<br>

## Documentation

Full docs: **[arkajojo.github.io/pbigen](https://arkajojo.github.io/pbigen/)**

| Guide | What's in it |
|-------|--------------|
| **[Recipes](https://github.com/arkajojo/pbigen/blob/main/docs/recipes.md)** | Copy-paste recipes for every feature. **Start here to build.** |
| **[Template packs](https://github.com/arkajojo/pbigen/blob/main/docs/templates.md)** | Turning any `.pbix` into a reusable design; what is captured; troubleshooting. |
| **[AI pipeline](https://github.com/arkajojo/pbigen/blob/main/docs/deterministic-vs-llm.md)** | The five stages, deterministic vs LLM, what is sent, research modes. |
| **[Sources](https://github.com/arkajojo/pbigen/blob/main/docs/sources.md)** | Every connector: install, authenticate, configure, test. |
| **[Models](https://github.com/arkajojo/pbigen/blob/main/docs/models.md)** | Any LLM provider (and local models) with env-var auth. |
| **[Themes](https://github.com/arkajojo/pbigen/blob/main/docs/themes.md)** · **[Testing](https://github.com/arkajojo/pbigen/blob/main/docs/testing.md)** · **[Publishing](https://github.com/arkajojo/pbigen/blob/main/docs/publishing.md)** | Theme JSON; self-serve verification; release runbook. |
| **[CHANGELOG](https://github.com/arkajojo/pbigen/blob/main/CHANGELOG.md)** | Release history. |

<br>

## FAQ

**Does it read my data?** No. Sources introspect metadata; Power BI loads data at refresh time on
your machine. `--profile` computes aggregates (min/max/top values) and only if you ask.

**Do I need an API key?** No. The deterministic engine builds the whole story offline. The AI
pipeline is optional and works with any provider or a local model.

**Will the template copy their charts?** No — it copies the *look* (canvas, chrome, fonts, styles,
theme). The charts, KPIs and story are designed for your data. For an exact clone of a specific
report, use Power BI Desktop's *Save as → .pbip*.

**What if the model makes a mistake?** Everything it returns is validated against your schema;
invalid fields are repaired or dropped, and if nothing valid remains pbigen falls back to the
deterministic design — and says so.

**Why PBIP/PBIR?** Microsoft's text-based report format: diffable, reviewable, CI-friendly.

<br>

## Contributing

Contributions are very welcome. Run `ruff check src tests` and `pytest` (fully offline) and open a
focused PR. See **[CONTRIBUTING.md](https://github.com/arkajojo/pbigen/blob/main/CONTRIBUTING.md)**.

## License

MIT © [Arka Gupta](https://github.com/arkajojo/pbigen/blob/main/AUTHORS.md). See [LICENSE](https://github.com/arkajojo/pbigen/blob/main/LICENSE).

## Disclaimer

pbigen is an **independent personal open-source project** by Arka Gupta. It is developed on personal
time and equipment, uses no employer code, data, credentials, or systems, and is **not affiliated
with, sponsored by, or endorsed by any employer**. All views and work here are the author's own.

<p align="center"><sub>Built by Arka Gupta · independent personal project.</sub></p>
