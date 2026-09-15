"""Let a language model refine the dashboard design.

Run:  python examples/generate_with_llm.py
Needs: pip install "dashforge[llm,lakehouse]"
       and a model + credentials, e.g. export OPENAI_API_KEY=sk-...
       (or run a local model: model="ollama/llama3", model_config={"api_base": "http://localhost:11434"})

Only metadata (column names, types, approximate distinct counts) is sent to the model — never rows.
If the model is unreachable or returns something unusable, dashforge falls back to the
deterministic design automatically.

Author: Arka Gupta
"""
from __future__ import annotations

from generate_from_parquet import make_sample  # reuse the sample builder

import dashforge


def main() -> None:
    make_sample("out/orders.parquet")
    result = dashforge.generate(
        "parquet",
        source_config={"uri": "out/orders.parquet"},
        objective="Executive revenue overview with trends and regional drivers",
        model="gpt-4o-mini",          # any LiteLLM model id, hosted or local
        theme="aurora",
        out_dir="out",
        name="OrdersLLM",
    )
    print(f"Designed by {result.model_name}: {result.n_pages} pages. Open: {result.pbip_path}")


if __name__ == "__main__":
    main()
