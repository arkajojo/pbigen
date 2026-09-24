# Recipes — copy-paste your way to a dashboard

Practical end-to-end examples for every feature. Each is self-contained. For per-source
authentication see [sources.md](sources.md); for every LLM provider see [models.md](models.md); for
themes/logo/shell see [themes.md](themes.md).

Every `generate` writes a **PBIP** project under `out/<name>/` (`.pbip` + `.Report` + `.SemanticModel`).
Open the `.pbip` in Power BI Desktop with the PBIR preview enabled (see the last recipe).

---

## 1. First dashboard, fully offline (no cloud, 30 seconds)

```bash
pip install "pbigen[lakehouse]" pyarrow
python - <<'PY'
import pyarrow as pa, pyarrow.parquet as pq, datetime, random
r=random.Random(1); n=500
pq.write_table(pa.table({
  "order_date":[datetime.date(2024,1,1)+datetime.timedelta(days=r.randint(0,540)) for _ in range(n)],
  "region":[r.choice(["North","South","East","West"]) for _ in range(n)],
  "status":[r.choice(["New","Shipped","Returned"]) for _ in range(n)],
  "revenue":[round(r.uniform(50,5000),2) for _ in range(n)],
  "quantity":[r.randint(1,20) for _ in range(n)]}), "orders.parquet")
PY
pbigen generate --source parquet --set uri=orders.parquet \
  --objective "Sales overview by region and status over time" --theme midnight --out out --name Demo
```

## 2. From a warehouse (BigQuery shown; any source is the same shape)

```bash
pip install "pbigen[bigquery]"
gcloud auth application-default login
pbigen test --source bigquery --set project=my-proj dataset=sales table=orders
pbigen generate --source bigquery --set project=my-proj dataset=sales table=orders \
  --objective "Revenue and orders by region over time" --theme midnight --out out
```
Swap in Snowflake, Redshift, Synapse/Fabric, Databricks, ClickHouse, Postgres, Athena, a
Parquet/Iceberg/Delta lake, or Cube — same commands, different `--source`/`--set` and auth
([sources.md](sources.md)).

## 3. Sample a huge table so it builds fast (BigQuery)

```bash
pbigen generate --source bigquery \
  --set project=bigquery-public-data dataset=chicago_taxi_trips table=taxi_trips billing_project=my-billing row_limit=50000 \
  --objective "Taxi trips by payment type and company over time" --theme slate --out out --name TaxiSample
```

## 4. Apply your corporate / a gallery theme

```bash
# download a theme .json (gallery: https://community.fabric.microsoft.com/t5/Themes-Gallery/bd-p/ThemesGallery)
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --theme ~/Downloads/CorporateTheme.json --out out --name Branded
# confirm it registered:
grep -o '"customTheme":{[^}]*}' out/Branded/Branded.Report/definition/report.json
```
Set `"sidebarColor"`/`"accentColor"` in the theme JSON to control the nav colour exactly
([themes.md](themes.md)).

## 5. Logo + right-hand navigation

```bash
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --theme midnight --logo ./assets/company_logo.png --nav right --out out --name RightNavLogo
```

## 6. Use a report you like as the design (template pack)

```bash
pbigen template build ~/Downloads/company_standard.pbix --out brand_pack
pbigen template show brand_pack            # canvas, content/filter/header regions, chrome, styles
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --template brand_pack --out out --name InOurDesign
# or in one step:  --template ~/Downloads/company_standard.pbix
```
Your pages, KPIs and story; their canvas, background, sidebar, logo, title font, theme and visual
formatting. Details: [templates.md](templates.md).

## 7. DirectQuery instead of Import

```bash
pbigen generate --source snowflake --set table=ORDERS database=ANALYTICS schema=SALES \
  --mode directquery --theme midnight --out out --name LiveOrders
```
DirectQuery keeps data live (needs a DQ-capable source — a warehouse, not a raw file).

## 8. Let the AI pipeline design the story (any provider)

```bash
pip install "pbigen[llm]"
export OPENAI_API_KEY=sk-…                 # or ANTHROPIC_API_KEY / GEMINI_API_KEY / …
pbigen doctor --model gpt-4o               # key works? web research available?
pbigen generate --source bigquery --set project=P dataset=D table=T \
  --model gpt-4o --research web --profile \
  --context "Ride-hailing operator; leadership wants more completed trips at higher margin" \
  --audience "COO and city managers" --template brand_pack --out out --name AIDesigned
# Gemini:    --model gemini/gemini-2.5-flash        (export GEMINI_API_KEY)
# Anthropic: --model anthropic/claude-sonnet-4-5    (export ANTHROPIC_API_KEY)
```
Five stages run (context → objectives & KPI tree → research → storyboard → critique); read the
reasoning in `out/AIDesigned/DESIGN.md`. `--context` also accepts a file path (a brief, meeting
notes). The CLI reports `using litellm:<model>`, or `deterministic (fallback …)` if no valid design
came back. Only metadata is sent — plus aggregates with `--profile`, never rows
([the pipeline](deterministic-vs-llm.md)).

## 9. Fully local model — nothing leaves your network

```bash
pip install "pbigen[llm]"
ollama serve &  ollama pull llama3
pbigen generate --source parquet --set uri=orders.parquet --model ollama/llama3 --out out --name Local
```

## 10. Python API (script it end to end)

```python
import pbigen

result = pbigen.generate(
    "bigquery",
    source_config={"project": "my-proj", "dataset": "sales", "table": "orders", "row_limit": 50000},
    objective="Revenue and orders by region over time",
    model="gpt-4o-mini",              # or None for deterministic
    theme="template/theme.json",      # built-in name or a path
    logo="template/assets/logo.png",
    nav="right",
    mode="import",
    out_dir="out",
    name="Programmatic",
)
print(result.pbip_path, "|", result.model_name, "|", result.n_pages, "pages")
```

## 11. Prove the output is valid (schema check)

```bash
pip install jsonschema referencing
python - <<'PY'
import glob, json, ssl, urllib.request
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
ctx=ssl.create_default_context(); c={}
def fetch(u):
    if u not in c:
        with urllib.request.urlopen(u,timeout=25,context=ctx) as r: c[u]=json.loads(r.read())
    return c[u]
reg=Registry(retrieve=lambda u: Resource.from_contents(fetch(u), default_specification=DRAFT7))
ok=bad=0
for f in glob.glob("out/**/definition/**/*.json", recursive=True):
    o=json.load(open(f)); s=o.get("$schema")
    if not s: continue
    e=list(Draft7Validator(fetch(s), registry=reg).iter_errors(o))
    ok+= not e; bad+= bool(e)
print("valid", ok, "invalid", bad)
PY
```

## 12. Open it in Power BI Desktop

1. One-time: **File → Options → Preview features → tick "Store reports using enhanced metadata
   format (PBIR)"** → restart.
2. If you moved the project (e.g. zipped to Windows), **extract the whole folder** — the `.pbip`,
   `.Report`, and `.SemanticModel` must stay together; never open the `.pbip` from inside a zip.
3. Open the `.pbip` → **Refresh** to load data through the generated connection.

---

See also: [testing.md](testing.md) (verification harness) · [sources.md](sources.md) ·
[models.md](models.md) · [themes.md](themes.md).
