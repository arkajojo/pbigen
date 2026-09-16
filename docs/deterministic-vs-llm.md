# Deterministic vs LLM — what to expect

pbigen has **two design brains**. The deterministic one runs by default; an LLM is optional. Both
produce a complete, schema-valid, openable Power BI project — they differ in *how the design is
decided*.

## Side by side

| | **Deterministic** (default) | **LLM-refined** (`--model …`) |
|---|---|---|
| Key / network needed | **None** | Provider key (or a local model) |
| Cost | **Free** | Provider usage (or free if local) |
| Reproducible | **Yes** — same inputs, same output | No — varies per call |
| What leaves your machine | **Nothing** | **Metadata only** (column names, types, approx. distinct counts) — never rows |
| Speed | Instant | A few seconds (one model call) |
| How it decides | Rules over data shape (types + cardinality) | The model reshapes pages/visuals/measures from the metadata + your objective |
| Safety net | n/a | Invalid references are dropped; on any error it **falls back to deterministic** |

## What the deterministic engine does

It classifies every column (measure / date / category / geo / id), proposes measures, and lays out a
narrative — **reliably and identically every time**:

- A date/time column becomes a **range filter**, never a 500-value dropdown.
- A breakdown with ≤ 8 categories → **donut**; more → **bar**.
- **Numeric geo/id codes** (census tract, community area, lat/long) are **never summed** into
  measures.
- **Legends are cardinality-guarded** — a high-cardinality field becomes a bar category, not a
  legend, so charts never error.
- Pages flow **Executive Summary → Trends → Segmentation → Detail**, each led by KPI cards, with a
  "how to use this report" note.

Use it when you want **predictable, governed, regenerable** dashboards (CI, many tables, no keys).

```bash
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --objective "Revenue and orders by region over time" --theme midnight --out out
# CLI prints:  … using deterministic.
```

## What the LLM adds

Pass `--model <id>` (any [LiteLLM](models.md) model — hosted or local) and the model **refines the
design**: it may pick a more relevant lead metric, a different chart mix, better titles, or a
narrative tuned to your objective. It sees **only metadata** — never row data.

```bash
export OPENAI_API_KEY=sk-…                          # or ANTHROPIC_API_KEY / GEMINI_API_KEY / …
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --objective "Where is revenue growing and where is it at risk?" \
  --model gpt-4o-mini --theme midnight --out out
# CLI prints:  … using litellm:gpt-4o-mini      (if it ran)
```

Use it when a table's "best story" isn't obvious from the shape alone and you want a smarter first
draft. Everything the model returns is **validated against the live schema** first.

## How to tell which one actually ran

The CLI summary (and `GenerateResult.model_name`) reports it honestly:

- `using deterministic` — the rules engine.
- `using litellm:<model>` — the LLM ran and its design was used.
- `using deterministic (fallback — <model> did not run; check the model id / credentials)` — the
  model couldn't be reached (bad key, rate limit, wrong id) and pbigen fell back. Your report is
  still complete; fix the credentials and re-run to get the LLM design.

To compare, generate the same table twice (with and without `--model`) and open both — the LLM
version's pages/visuals will differ.

## Privacy, both ways

- **Deterministic:** nothing leaves your machine at all.
- **LLM:** only **metadata** is sent — column names, canonical types, approximate distinct counts —
  plus your objective string. **No rows.** For zero egress even with a model, run a **local** one
  (`--model ollama/llama3`). See [Models](models.md).

## Recommendation

Start **deterministic** — it's free, instant, reproducible, and already produces clean, executive
dashboards. Reach for an **LLM** when you want a sharper narrative on a specific question, and prefer
a **local model** if data-governance rules forbid any external calls.
