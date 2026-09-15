# Testing pbigen — a self-serve guide for every source and model

This is the guide to hand a teammate. It shows how to prove pbigen works against **any** source and,
optionally, with **any** language model — from a 30-second offline check to a full BigQuery matrix
validated against Microsoft's schemas.

Nothing here mutates your data. Sources are **read-only** and introspect **metadata only**; models
(if you use one) receive metadata only. No row data leaves your machine.

---

## 0. Install

```bash
pip install "pbigen[<source-extra>]"     # e.g. pbigen[bigquery] — see docs/sources.md for the extra
pip install "pbigen[llm]"                # only if you want an LLM-refined design
pip install jsonschema referencing       # only for the optional schema-validation step below
```

Sanity check with no credentials at all:
```bash
pbigen --version
pbigen sources          # lists all 16 source kinds
pbigen themes           # midnight | slate | aurora
```

## 1. Prove it end-to-end offline (30 seconds, no cloud account)

The fastest "does it actually work" — generate from a local Parquet file:
```bash
pip install "pbigen[lakehouse]" pyarrow
python examples/generate_from_parquet.py       # builds a sample file, generates a project
# → prints the .pbip path; open it in Power BI Desktop (PBIR preview) and Refresh
```
If this produces an openable project, the whole pipeline (introspect → design → layout → emit) works
on your machine. Everything below is the same flow pointed at a real source.

## 2. The universal 6-step verification (any source)

Pick your source from **[docs/sources.md](sources.md)** for the exact `--set` keys and auth, then:

```bash
# 1) install the driver
pip install "pbigen[<extra>]"

# 2) authenticate (env vars — see docs/sources.md for your source)
#    e.g. gcloud auth application-default login   |   export AWS_ACCESS_KEY_ID=… etc.

# 3) connectivity + introspection (read-only, ~seconds)
pbigen test --source <kind> --set <key=value ...>
#    → "<kind>: OK — N columns in <table>"

# 4) generate (deterministic — no model, no key)
pbigen generate --source <kind> --set <key=value ...> --theme midnight --out out --name Check_Deterministic

# 5) (optional) generate with a language model refining the design
export OPENAI_API_KEY=sk-…        # or any provider's key — see docs/models.md
pbigen generate --source <kind> --set <key=value ...> \
  --model gpt-4o-mini --theme midnight --out out --name Check_LLM

# 6) open each out/<name>/<name>.pbip in Power BI Desktop (PBIR preview enabled) and Refresh
```

### What "working" looks like
- **Step 3** prints `OK — N columns` → auth + introspection succeed.
- **Step 4** prints `model used: deterministic`, a page/visual summary, and writes `…/<name>.pbip`.
- **Step 5** prints `model used: litellm:<model>` and a **different** design (the LLM reshaped it).
- **Step 6**: the report opens in Desktop with a sidebar + filters + KPI cards + charts; Refresh loads data.

## 3. Validate the output against Microsoft's PBIR schemas (optional, high-confidence)

Beyond "it opens," you can prove every generated report file is schema-correct:

```python
# save as check_schema.py, then:  python check_schema.py out/Check_Deterministic/Check_Deterministic.Report
import sys, json, glob, ssl, urllib.request
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ctx = ssl.create_default_context(); cache = {}
def fetch(u):
    if u not in cache:
        with urllib.request.urlopen(u, timeout=25, context=ctx) as r: cache[u] = json.loads(r.read())
    return cache[u]
reg = Registry(retrieve=lambda u: Resource.from_contents(fetch(u), default_specification=DRAFT7))

report_dir = sys.argv[1]; ok = bad = 0
for path in glob.glob(f"{report_dir}/definition/**/*.json", recursive=True):
    obj = json.load(open(path)); su = obj.get("$schema")
    if not su: continue
    errs = sorted(Draft7Validator(fetch(su), registry=reg).iter_errors(obj), key=lambda e: e.path)
    if errs: bad += 1; print("INVALID", path.split("definition/")[1], "-", errs[0].message[:120])
    else: ok += 1
print(f"valid={ok} invalid={bad}")
```
Expect `valid=N invalid=0`.

## 4. The full BigQuery matrix (deterministic × LLM, built-in × custom theme)

`examples/verify_bigquery.py` runs **four** generations from the *same* BigQuery table and validates
each against Microsoft's schemas — the most comprehensive single check:

| Run | Model | Theme |
|-----|-------|-------|
| A | deterministic | built-in `midnight` |
| B | Gemini | built-in `midnight` |
| C | deterministic | custom `examples/custom_theme.json` |
| D | Gemini | custom `examples/custom_theme.json` |

```bash
pip install "pbigen[bigquery,llm]" jsonschema referencing
gcloud auth application-default login
export BQ_PROJECT=your-project BQ_DATASET=your_dataset BQ_TABLE=your_table
export GEMINI_API_KEY=…                      # optional; B and D auto-skip without it
# export PBIGEN_GEMINI_MODEL=gemini/gemini-2.5-pro   # optional override

python examples/verify_bigquery.py
```
For each run it prints the model used, the page/visual design, and
`ALL N report files valid against Microsoft's PBIR schemas`. Swap the source and it's the pattern for
any warehouse; swap `custom_theme.json` for your corporate theme to test brand fidelity.

**Reading the results:**
- A vs. B (and C vs. D): the **design differs** → the model was genuinely called and applied.
- A/B vs. C/D: colours/sidebar differ; in each project's `…Report/definition/report.json`,
  `themeCollection.customTheme.name` reflects the theme used (`"Acme Corporate"` for C/D).

## 5. Test a language model on its own

Any provider works — set that provider's env var and pass `--model` (full matrix in
**[docs/models.md](models.md)**):

```bash
# OpenAI
export OPENAI_API_KEY=sk-…;         pbigen generate … --model gpt-4o-mini
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-…;  pbigen generate … --model anthropic/claude-sonnet-4-6
# Google Gemini (AI Studio)
export GEMINI_API_KEY=…;            pbigen generate … --model gemini/gemini-2.5-flash
# Fully local, open-source (nothing leaves your network)
ollama serve & ollama pull llama3;  pbigen generate … --model ollama/llama3
```
If a model can't be reached, pbigen falls back to the deterministic design and the summary shows
`deterministic` — a safe, visible signal rather than a crash.

## 6. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `unknown source 'x'` | Typo or extra not installed — run `pbigen sources`; `pip install "pbigen[<extra>]"`. |
| `ModuleNotFoundError` for a driver | Install the source's extra (e.g. `pbigen[snowflake]`). |
| `pbigen test` auth error | Re-check the env vars in docs/sources.md for that source; for BigQuery run `gcloud auth application-default login`. |
| Synapse/Fabric: `Can't open lib 'ODBC Driver 18…'` | Install msodbcsql18 (see docs/sources.md → Synapse). |
| Model run shows `deterministic` | The key/endpoint was missing or the call failed → it fell back. Check the provider env var. |
| Visuals empty in Desktop | Enable the PBIR preview: **Options → Preview features → "Store reports using enhanced metadata format"**, restart. |
| Iceberg/Delta won't refresh in Desktop | Expected for raw cloud tables — refresh via a Fabric Lakehouse / Databricks SQL endpoint (docs/sources.md → Refresh note). |

---

See also: **[docs/sources.md](sources.md)** (per-source auth + config) · **[docs/models.md](models.md)**
(every LLM provider) · the repo **[README](../README.md)**.
