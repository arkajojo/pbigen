# Models

A *model* turns table metadata plus a plain-language objective into a design brief — which pages,
which visuals, which filters, and the usage notes. pbigen ships two:

## Deterministic (default)

No API key, no network, no cost, fully reproducible. It runs the rule-based design brain, which
already reasons about canonical types and cardinality:

- a date/time column becomes a **range filter**, never a dropdown of hundreds of values;
- a breakdown with ≤ 8 categories becomes a **donut**, otherwise a **bar**;
- wide breakdowns go into a **matrix**; every page leads with **KPI cards**;
- high-cardinality ids and redundant period columns are kept out of the filters.

```python
pbigen.generate("bigquery", source_config={...})            # deterministic by default
pbigen.generate(..., model="deterministic")                 # explicit
```

## Bring your own model (LiteLLM)

Pass any [LiteLLM](https://github.com/BerriAI/litellm) model id to let a language model refine the
design. LiteLLM speaks to ~100 providers with one interface, hosted or local:

```python
# hosted (key from the provider's standard env var, e.g. OPENAI_API_KEY / ANTHROPIC_API_KEY)
pbigen.generate(..., model="gpt-4o-mini")
pbigen.generate(..., model="anthropic/claude-sonnet-4-6")

# local, fully open-source — no data leaves your machine
pbigen.generate(..., model="ollama/llama3",
                   model_config={"api_base": "http://localhost:11434"})

# explicit key / endpoint instead of env vars
pbigen.generate(..., model="gpt-4o-mini",
                   model_config={"api_key": "sk-...", "temperature": 0.1})
```

```bash
pip install "pbigen[llm]"
pbigen generate --source snowflake --set ... --model gpt-4o-mini
```

### What the model sees

**Only metadata** — column names, canonical types, and approximate distinct counts. No row data is
ever sent. The prompt asks for a strict JSON design, and pbigen validates every field the model
returns against the live schema: unknown columns, invalid visual types and dangling measure
references are dropped. If the model is unreachable or returns something unusable, pbigen falls
back to the deterministic design, so generation never hard-fails.

## Writing your own model

Implement one method:

```python
from pbigen.models.base import Model
from pbigen.core.design import Design, design as deterministic

class MyModel(Model):
    name = "my-model"
    def design(self, schema, objective) -> Design:
        base = deterministic(schema, objective)   # a solid starting point
        ...                                        # refine and return a Design
        return base

pbigen.generate(..., model=MyModel())
```
