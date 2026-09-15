"""Shared fixtures.

A small, self-contained Parquet dataset gives us a real source to exercise the whole pipeline
offline — introspection, cardinality, design and Power BI emission — with no cloud credentials.

Author: Arka Gupta
"""
from __future__ import annotations

import datetime
import random

import pytest


@pytest.fixture(scope="session")
def orders_parquet(tmp_path_factory) -> str:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    rng = random.Random(7)
    regions = ["North", "South", "East", "West"]
    products = ["Alpha", "Beta", "Gamma"]
    statuses = ["New", "Shipped", "Returned"]
    n = 400
    table = pa.table({
        "order_date": [datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 540)) for _ in range(n)],
        "region": [rng.choice(regions) for _ in range(n)],
        "product": [rng.choice(products) for _ in range(n)],
        "status": [rng.choice(statuses) for _ in range(n)],
        "order_id": [f"ORD{i:05d}" for i in range(n)],
        "revenue": [round(rng.uniform(50, 5000), 2) for _ in range(n)],
        "quantity": [rng.randint(1, 20) for _ in range(n)],
    })
    path = tmp_path_factory.mktemp("data") / "orders.parquet"
    pq.write_table(table, str(path))
    return str(path)


@pytest.fixture(scope="session")
def sqlite_url(tmp_path_factory) -> str:
    sa = pytest.importorskip("sqlalchemy")
    path = tmp_path_factory.mktemp("db") / "orders.db"
    url = f"sqlite:///{path}"
    eng = sa.create_engine(url)
    with eng.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE orders (region TEXT, product TEXT, revenue REAL, quantity INTEGER)"
        ))
        conn.execute(sa.text("INSERT INTO orders VALUES ('North','Alpha',100.0,2),"
                             "('South','Beta',250.5,5),('East','Alpha',75.0,1)"))
    return url
