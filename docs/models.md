# Models — deterministic by default, any LLM optional

A *model* turns table **metadata** plus a plain-language objective into a design brief — which pages,
which visuals, which filters, and the usage notes. pbigen ships two backends.

> **Privacy (applies to every provider below):** only **metadata** — column names, canonical types
> and approximate distinct counts — is ever sent to a model. **No row data leaves your machine.**
> Every field the model returns is validated against the live schema; if the model is unreachable or
> returns something unusable, pbigen falls back to the deterministic design, so generation never
> hard-fails.

## Deterministic (default) — no key, no network, no cost

Runs the rule-based, cardinality-aware design engine. This is what you get with no `--model`:

```bash
pbigen generate --source <kind> --set … --theme midnight --out out          # deterministic
```
```python
pbigen.generate("<kind>", source_config={…})                                # deterministic
pbigen.generate("<kind>", source_config={…}, model="deterministic")         # explicit
```

## Any LLM via LiteLLM — install once

```bash
pip install "pbigen[llm]"
```
pbigen uses [LiteLLM](https://github.com/BerriAI/litellm), which speaks to ~100 providers with one
interface. You pick the model with `--model <id>` (CLI) or `model="<id>"` (Python); credentials come
from the provider's standard **environment variables** (or pass them explicitly — see the bottom).

### Provider matrix

| Provider | Install extra | Model id (`--model`) | Authenticate |
|----------|---------------|----------------------|--------------|
| **OpenAI** | `pbigen[llm]` | `gpt-4o-mini`, `gpt-4o`, `openai/o4-mini` | `export OPENAI_API_KEY=sk-…` |
| **Anthropic** | `pbigen[llm]` | `anthropic/claude-sonnet-4-6`, `anthropic/claude-3-5-haiku-latest` | `export ANTHROPIC_API_KEY=sk-ant-…` |
| **Google — AI Studio** | `pbigen[llm]` | `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-pro` | `export GEMINI_API_KEY=…`  (from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)) |
| **Google — Vertex AI** | `pbigen[llm]` | `vertex_ai/gemini-2.5-flash` | `gcloud auth application-default login` + `export VERTEXAI_PROJECT=… VERTEXAI_LOCATION=us-central1` |
| **Azure OpenAI** | `pbigen[llm]` | `azure/<your-deployment-name>` | `export AZURE_API_KEY=… AZURE_API_BASE=https://<res>.openai.azure.com/ AZURE_API_VERSION=2024-08-01-preview` |
| **AWS Bedrock** | `pbigen[llm]` | `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` | standard AWS creds (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` or a role) + `export AWS_REGION=us-east-1` |
| **Ollama (local, open-source)** | `pbigen[llm]` | `ollama/llama3`, `ollama/qwen2.5` | run `ollama serve`; endpoint `http://localhost:11434` |
| **vLLM / LM Studio / any OpenAI-compatible** | `pbigen[llm]` | `openai/<model>` | point `api_base` at your server; key can be a placeholder |

LiteLLM supports far more (Mistral, Cohere, Groq, Together, OpenRouter, …) with the same pattern —
`--model <provider>/<model>` + that provider's env var. See LiteLLM's provider docs for exact ids.

### Examples

**Hosted, key from the environment:**
```bash
export OPENAI_API_KEY=sk-…
pbigen generate --source bigquery --set project=p dataset=d table=t \
  --model gpt-4o-mini --theme midnight --out out
```
```bash
export GEMINI_API_KEY=…
pbigen generate --source snowflake --set table=ORDERS database=ANALYTICS schema=SALES \
  --model gemini/gemini-2.5-flash --theme midnight --out out
```

**Fully local, open-source (nothing leaves your network):**
```bash
ollama serve &                      # in another shell: ollama pull llama3
pbigen generate --source parquet --set uri=./sales.parquet --model ollama/llama3 --out out
```
Python (set the endpoint via `model_config`):
```python
pbigen.generate("parquet", source_config={"uri": "sales.parquet"},
                model="ollama/llama3",
                model_config={"api_base": "http://localhost:11434"})
```

**Pass key/endpoint explicitly instead of env vars** (Python):
```python
pbigen.generate("bigquery", source_config={…},
                model="gpt-4o-mini",
                model_config={"api_key": "sk-…", "temperature": 0.1, "max_tokens": 4000})
```

### How to tell the model actually ran

`GenerateResult.model_name` (Python) and the CLI summary report the backend used:
`deterministic` vs. e.g. `litellm:gpt-4o-mini`. With a model, the generated **pages/visuals differ**
from the deterministic run — that's the model reshaping the design. If a run silently falls back
(bad key, no network), you'll see `deterministic` even though you passed `--model`.

## Writing your own model

Implement one method and hand pbigen an instance (Python API):
```python
from pbigen.models.base import Model
from pbigen.core.design import design as deterministic

class MyModel(Model):
    name = "my-model"
    def design(self, schema, objective):
        base = deterministic(schema, objective)   # a solid starting point
        # …refine and return a Design…
        return base

pbigen.generate("bigquery", source_config={…}, model=MyModel())
```
