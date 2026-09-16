# Why pbigen — in a world full of AI & agentic BI

AI dashboard generation is crowded in 2026: **Power BI Copilot & Agent Skills**, agentic BI
platforms like **ThoughtSpot, Tableau Pulse, Sigma, Domo, Tellius**, and general **LLMs** (ChatGPT,
Claude) that can sketch charts. They're capable. So where does a small open-source library fit?

**pbigen is the open, local, file-first option.** It turns a table into **portable Power BI files you
own** — generated on your machine, for free, deterministically if you want, with **no data leaving
your environment**. It doesn't compete with a chat surface; it produces version-controllable
artifacts that drop into the Power BI workflow your organization already runs.

## The detailed comparison

| | **pbigen** | Power BI Copilot / Agent Skills | Agentic BI platforms<br>(ThoughtSpot · Sigma · Tableau Pulse · Domo · Tellius) | General LLM<br>(ChatGPT / Claude) | Build by hand |
|---|:---:|:---:|:---:|:---:|:---:|
| **Output is native Power BI you own** (PBIP files) | ✅ | ⚠️ built in the service | ❌ their own BI surface | ❌ snippets only | ✅ |
| **Version-controlled, CI-friendly** text (PBIR + TMDL) | ✅ | ⚠️ not the generation flow | ❌ | ❌ | ⚠️ only if you enable PBIR |
| **Runs locally / in CI**, no paid cloud capacity | ✅ | ❌ needs Fabric capacity (F2+) | ❌ SaaS subscription | ⚠️ API/subscription | ✅ Desktop |
| **Works with no LLM / no API key** (deterministic) | ✅ | ❌ requires their AI | ❌ | ❌ | ✅ |
| **Reproducible** output (same inputs → same result) | ✅ | ❌ | ❌ | ❌ | ⚠️ human-dependent |
| **One interface across warehouses + lakehouse (Iceberg/Delta) + semantic layer**, multi-cloud | ✅ | ⚠️ Fabric / OneLake-centric | ⚠️ varies by vendor | ❌ | ⚠️ manual per connector |
| **Metadata-only** — no row data leaves your environment to design | ✅ | ⚠️ cloud service | ⚠️ SaaS | ❌ you paste data | ✅ |
| **Match a house style** — theme + logo + nav, or clone a `.pbix` shell | ✅ | ⚠️ manual | ❌ | ❌ | ⚠️ manual |
| **Open source (MIT)**, self-hostable, extensible | ✅ | ❌ | ❌ | ❌ | n/a |
| **Cost** | **Free** | Paid (Fabric capacity) | Paid (per-seat SaaS) | Usage-based | Free (Desktop) |

*⚠️ = partial or conditional; reflects each tool's common default in 2026, not every edge case.*

## What each alternative is great at — and where pbigen wins

### Power BI Copilot / Agent Skills
Microsoft's in-product AI is powerful and native — it drafts pages, writes DAX, and (with Agent
Skills) does end-to-end agentic authoring. But it **lives inside Fabric**, needs **paid capacity**,
works **in the service** (not as version-controlled files you generate in CI), and is
**non-reproducible**. pbigen wins when you want **free, local, deterministic, git-tracked** Power BI
that any teammate can regenerate identically — and it happily coexists (generate the baseline with
pbigen, refine with Copilot).

### Agentic BI platforms (ThoughtSpot, Sigma, Tableau Pulse, Domo, Tellius)
Excellent conversational analytics — but they build dashboards **in their own surface** and bill
**per seat**. If your organization standardizes on **Power BI**, their output doesn't live there.
pbigen produces **Power BI**, on your terms, for free.

### General LLMs (ChatGPT, Claude)
Great for a one-off chart or a DAX snippet, and you can paste data in. But they don't emit a
**complete, connected, refreshable Power BI project**, they're **not reproducible**, and pasting rows
means **your data leaves your environment**. pbigen sends **only metadata** to an optional LLM — and
needs none at all by default.

### Building by hand
The gold standard for a bespoke, pixel-perfect report — and the right tool for exactly cloning one
existing report (Desktop's *Save as .pbip*). But it's **slow and inconsistent** at scale. pbigen does
the mechanical 90% (connect, model, measure, chart-select, lay out, theme) in seconds, leaving you
the 10% that needs judgement.

## The moat, honestly

- **Correct PBIP/PBIR/TMDL emission is hard.** pbigen's output validates against Microsoft's
  *published* schemas, every file, every run — so projects open in Desktop without repair.
- **A real design brain, not a prompt.** Column-role classification, cardinality-driven chart/filter
  choices, geo/id exclusion, legend guards, safe DAX — reproducible and free, LLM optional.
- **Breadth behind one contract.** 16 sources across every major cloud + lakehouse + a semantic
  layer, all through the same `introspect → cardinality → connect` interface.
- **Enterprise-safe by construction.** Read-only, metadata-only, no capacity to buy, no egress.

## When *not* to use pbigen (we'd rather be honest)

- **You need an exact clone of one existing report on the same data** → use Power BI Desktop's
  **File → Save as → `.pbip`** (or `pbi-tools`). pbigen reuses a *shell*, it doesn't clone a specific
  report.
- **You want a live natural-language Q&A chat over your data** → that's Copilot / ThoughtSpot
  territory, not a file generator.
- **You're not on Power BI at all** → pbigen emits Power BI; a Looker/Tableau shop wants a different
  tool.

Everywhere else — "I have a table (or 200) and I want clean, on-brand, governed Power BI I can
regenerate and version" — pbigen is built exactly for that.

Ready? [**Start with the recipes →**](recipes.md)
