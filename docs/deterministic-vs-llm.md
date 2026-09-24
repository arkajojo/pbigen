# The design engines — deterministic and the AI pipeline

pbigen has **two design engines**. Both produce a complete, story-structured, schema-valid Power BI
project; they differ in how deeply they reason about the *business*.

| | **Deterministic** (default) | **AI pipeline** (`--model …`) |
|---|---|---|
| Key / network | **None** | A provider key (or a local model) |
| Cost | **Free** | Provider usage (free if local) |
| Reproducible | **Yes** | No — varies per run |
| What leaves your machine | **Nothing** | Metadata only (+ aggregate profiles with `--profile`) — never rows |
| Time | Instant | ~1-3 minutes (five stages; web research is the slowest) |
| Reasoning | Data shape + a keyword-matched domain playbook | Business context → objectives & KPI tree → research → storyboard → critique |
| Safety net | n/a | Everything validated against the schema; falls back to deterministic if nothing valid remains |

Both engines get the same finishing: **monthly trend grain**, **period-over-period deltas** on every KPI
card, an **About this report** page with KPI definitions, and a **`DESIGN.md`** with the reasoning.

## The deterministic engine

Rules over the data shape — reliable and identical every time:

- **KPI set named after the grain** — `Trips`, `Orders` (not "Record Count"), distinct entities
  (`Unique Customers`), totals, averages and an efficiency ratio (`Avg Revenue per Order`).
  Cost-like measures are marked *lower is better* so their deltas turn red when they rise.
- **Domain playbook** — columns are matched against built-in playbooks (mobility, commerce,
  marketing, product, finance, operations, service, HR, SaaS, healthcare) for the north star and
  objectives written into the About page and `DESIGN.md`.
- **The story** — *Executive Summary* (KPI band, hero combo of volume vs value, main driver, ranked
  top segments, efficiency) → *Trends Over Time* (monthly trends, mix over time) → *Drivers &
  Segments* (ranked bars per dimension, treemap for long tails, scorecard matrix, volume-vs-value
  scatter) → *Detailed Data* → *About this report*.
- **Shape rules** — dates are range sliders; donuts only for ≤ 6 slices, otherwise ranked bars;
  legends only for ≤ 6 values; ids and codes never summed or charted.

## The AI pipeline

```bash
pip install "pbigen[llm]"
export OPENAI_API_KEY=...     # or ANTHROPIC_API_KEY / GEMINI_API_KEY, or a local model
pbigen generate --source ... --model gpt-4o \
  --context brief.md --audience "CFO and finance BPs" --research web --profile
```

Five stages, each an expert persona with the curated knowledge base and a strict JSON contract;
every stage sees what the earlier ones concluded:

1. **Business context** (*principal analytics consultant*) — domain, business model, the grain
   ("one row = one trip"), entities, processes, the audience and the decisions they make, what each
   column means (units included), assumptions and caveats.
2. **Objectives & KPI tree** (*head of strategy & analytics*) — the north star; 3-5 objectives, each
   with the decisions it informs and prioritised questions; 6-12 KPIs with exact formulas, unit and
   which direction is good; **gaps** the data cannot answer (and what data would).
3. **Research** (*BI research analyst*) — how leading organisations in the domain measure and
   visualise these objectives: findings with implications, standard KPIs, recommended views,
   benchmarks, pitfalls. `--research web` uses live web search where the provider supports it
   (OpenAI search models / GPT-5, Anthropic, Gemini) and cites sources; otherwise — or with
   `--research builtin` (default) — it builds on the curated playbooks. `--research off` skips it.
4. **Storyboard** (*IBCS-trained dashboard designer*) — 4-6 pages, one headline question per page,
   the right chart per question, a subtitle on every visual, layout sizes, filters, and a coverage
   map from objectives to visuals.
5. **Critique & repair** (*the most demanding reviewer*) — coverage (every objective and KPI),
   story flow, chart fitness, clarity, validity — then returns the corrected design.
   Skip with `--no-critique`.

### What the model can express

KPIs: `agg` (SUM / AVERAGE / MIN / MAX / COUNT / DISTINCTCOUNT of a column), `ratio`
(SUM(a) / SUM(b) of columns) and KPI-on-KPI `divide` / `add` / `subtract` / `multiply`
(`Net Revenue = Gross Revenue − Total Discount`). Never raw DAX — pbigen writes the DAX.

Visuals: card, line, area, column, bar, stacked column/bar, combo (columns + line), waterfall,
donut, pie, treemap, scatter, matrix, table — each with title, subtitle, size (hero / side / half /
third / full), ranking and data labels.

### Validation — the model can never break the report

- unknown columns and undefined KPIs are dropped; KPI-on-KPI formulas are resolved in order,
- donuts with > 6 slices become ranked bars; legends with > 6 values are removed,
- trends on a timestamp are moved to the monthly grain,
- stacked charts without a series become plain charts; combos without a line become columns,
- high-cardinality slicers are dropped; model-made "About" pages are replaced by pbigen's own.

If a stage fails it is recorded and the run continues; if no valid design emerges, the
deterministic design is used, and the CLI says `deterministic (fallback — …)`.

### What is sent

Column names, canonical types, approximate distinct counts, your objective / context / audience
text. With `--profile`: min / max / average of numeric columns, date ranges, and the top 5 values
of low-cardinality text columns. **Never rows.** For zero egress, use a local model
(`--model ollama/llama3.1`).

## Which to use

- **Deterministic** for CI, many tables, governed regeneration, or no keys.
- **AI pipeline** when the story matters — a new domain, an executive audience, a specific question.
  Give it a `--context` brief: two sentences about the business and what leadership cares about
  make a visible difference. Frontier models (GPT-4o/5, Claude Sonnet/Opus, Gemini 2.5 Pro) tell the
  best stories.

Read the generated **`DESIGN.md`** either way — it is the fastest way to review what was built and why.
