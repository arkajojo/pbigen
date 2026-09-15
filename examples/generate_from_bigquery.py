"""Generate a Power BI dashboard from a BigQuery table.

Run:  python examples/generate_from_bigquery.py
Needs: pip install "pbigen[bigquery]"
       Application Default Credentials: gcloud auth application-default login

Also covers BigLake and BigQuery Omni tables — they use the same adapter.

Author: Arka Gupta
"""
from __future__ import annotations

import pbigen


def main() -> None:
    result = pbigen.generate(
        "bigquery",
        source_config={
            "project": "my-project",     # <- your GCP project
            "dataset": "sales",          # <- your dataset
            "table": "orders",           # <- your table or view
        },
        objective="Sales performance by region and product over time",
        theme="slate",
        out_dir="out",
    )
    print(f"Generated {result.n_pages} pages. Open: {result.pbip_path}")


if __name__ == "__main__":
    main()
