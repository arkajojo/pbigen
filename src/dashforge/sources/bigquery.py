"""Google BigQuery source — also covers BigLake and BigQuery Omni.

BigLake tables (external data in GCS with fine-grained governance) and BigQuery Omni tables
(data in AWS S3 / Azure ADLS queried through BigQuery) are ordinary BigQuery relations: they
introspect and query through the same API and connect in Power BI via the same connector.

Author: Arka Gupta
"""
from __future__ import annotations

import os

from ..core.schema import (
    BOOLEAN,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INTEGER,
    STRING,
    TIME,
    Column,
    Schema,
)
from .base import Source

_TYPE_MAP = {
    "STRING": STRING, "BYTES": STRING, "JSON": STRING, "GEOGRAPHY": STRING,
    "INTEGER": INTEGER, "INT64": INTEGER,
    "FLOAT": FLOAT, "FLOAT64": FLOAT,
    "NUMERIC": DECIMAL, "BIGNUMERIC": DECIMAL, "DECIMAL": DECIMAL,
    "BOOLEAN": BOOLEAN, "BOOL": BOOLEAN,
    "DATE": DATE, "DATETIME": DATETIME, "TIMESTAMP": DATETIME, "TIME": TIME,
}


class BigQuerySource(Source):
    kind = "bigquery"

    def __init__(self, table: str, dataset: str, project: str,
                 billing_project: str | None = None, location: str | None = None):
        self.table = table
        self.dataset = dataset
        self.project = project
        self.billing_project = billing_project or os.environ.get("BQ_BILLING_PROJECT") or project
        self.location = location
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.billing_project, location=self.location)
        return self._client

    def introspect(self) -> Schema:
        client = self._get_client()
        ref = f"{self.project}.{self.dataset}.{self.table}"
        tbl = client.get_table(ref)  # metadata only, no scan
        columns = [Column(f.name, _TYPE_MAP.get(f.field_type.upper(), STRING)) for f in tbl.schema]
        return Schema(self.table, columns, display_name=self.table.replace("_", " ").title())

    def approx_distinct(self, columns: list[str]) -> dict[str, int]:
        if not columns:
            return {}
        sel = ", ".join(f"APPROX_COUNT_DISTINCT(`{c}`) AS c{i}" for i, c in enumerate(columns))
        sql = f"SELECT {sel} FROM `{self.project}`.{self.dataset}.`{self.table}`"
        try:
            row = next(iter(self._get_client().query(sql).result()))
            return {c: int(row[i]) for i, c in enumerate(columns) if row[i] is not None}
        except Exception:  # noqa: BLE001 - cardinality is best-effort
            return {}

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = GoogleBigQuery.Database([BillingProject="{self.billing_project}"]),\n'
            f'  Project = Source{{[Name="{self.project}"]}}[Data],\n'
            f'  Dataset = Project{{[Name="{self.dataset}", Kind="Schema"]}}[Data],\n'
            f'  Data = Dataset{{[Name="{self.table}", Kind="Table"]}}[Data]\n'
            "in Data"
        )
