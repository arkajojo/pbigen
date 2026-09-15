"""Generate a Power BI dashboard from a local Parquet file — fully offline.

Run:  python examples/generate_from_parquet.py
Needs: pip install "dashforge[lakehouse]" pyarrow

Author: Arka Gupta
"""
from __future__ import annotations

import datetime
import os
import random

import pyarrow as pa
import pyarrow.parquet as pq

import dashforge


def make_sample(path: str, n: int = 500) -> None:
    rng = random.Random(7)
    regions = ["North", "South", "East", "West"]
    products = ["Alpha", "Beta", "Gamma"]
    statuses = ["New", "Shipped", "Returned"]
    table = pa.table({
        "order_date": [datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 540)) for _ in range(n)],
        "region": [rng.choice(regions) for _ in range(n)],
        "product": [rng.choice(products) for _ in range(n)],
        "status": [rng.choice(statuses) for _ in range(n)],
        "revenue": [round(rng.uniform(50, 5000), 2) for _ in range(n)],
        "quantity": [rng.randint(1, 20) for _ in range(n)],
    })
    pq.write_table(table, path)


def main() -> None:
    os.makedirs("out", exist_ok=True)
    data = os.path.join("out", "orders.parquet")
    make_sample(data)

    result = dashforge.generate(
        "parquet",
        source_config={"uri": data},
        objective="Revenue and orders by region and product over time",
        theme="midnight",
        out_dir="out",
        name="OrdersDemo",
    )
    print(f"Generated {result.n_pages} pages from {result.table} ({result.n_columns} columns).")
    print(f"Open in Power BI Desktop: {result.pbip_path}")


if __name__ == "__main__":
    main()
