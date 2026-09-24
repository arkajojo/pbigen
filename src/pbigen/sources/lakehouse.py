"""Lakehouse / open-table source powered by DuckDB.

One adapter reads **Parquet**, **Apache Iceberg** and **Delta Lake** sitting on **local disk,
GCS, S3 or ADLS**. DuckDB does the metadata read (schema + cardinality) with no cluster; cloud
credentials are picked up from the environment via DuckDB secrets.

Introspection is fully portable. For Power BI refresh, raw Parquet is reachable via the storage
connectors; Iceberg/Delta are best consumed through a Fabric Lakehouse or Databricks endpoint —
see ``power_query`` and docs/sources.md.

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
from .base import Source, profile_via_sql

_FORMATS = {
    "parquet": "read_parquet('{uri}')",
    "delta": "delta_scan('{uri}')",
    "iceberg": "iceberg_scan('{uri}')",
}


def _canonical(duck_type: str) -> str:
    t = duck_type.upper()
    if t.startswith("DECIMAL") or t == "HUGEINT":
        return DECIMAL
    if any(k in t for k in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "INT")):
        return INTEGER
    if any(k in t for k in ("DOUBLE", "FLOAT", "REAL")):
        return FLOAT
    if "BOOL" in t:
        return BOOLEAN
    if "TIMESTAMP" in t:
        return DATETIME
    if t == "DATE":
        return DATE
    if t == "TIME":
        return TIME
    return STRING


class LakehouseSource(Source):
    kind = "lakehouse"

    def __init__(self, uri: str, fmt: str = "parquet", display_name: str | None = None):
        fmt = fmt.lower()
        if fmt not in _FORMATS:
            raise ValueError(f"unsupported lakehouse format {fmt!r}; use one of {sorted(_FORMATS)}")
        self.uri = uri
        self.fmt = fmt
        self._display = display_name or os.path.splitext(os.path.basename(uri.rstrip("/")))[0]
        self._con = None

    # -- duckdb connection with the right extensions + cloud secrets --
    def _connect(self):
        if self._con is not None:
            return self._con
        import duckdb
        con = duckdb.connect()
        for ext in ("parquet", "httpfs", self.fmt):
            try:
                con.execute(f"INSTALL {ext}; LOAD {ext};")
            except Exception:  # noqa: BLE001 - builtin/offline extensions
                pass
        self._setup_cloud_secret(con)
        self._con = con
        return con

    def _setup_cloud_secret(self, con) -> None:
        u = self.uri.lower()
        try:
            if u.startswith("s3://"):
                con.execute(
                    "CREATE OR REPLACE SECRET s3 (TYPE S3, KEY_ID ?, SECRET ?, REGION ?)",
                    [os.environ.get("AWS_ACCESS_KEY_ID", ""), os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
                     os.environ.get("AWS_REGION", "us-east-1")],
                )
            elif u.startswith(("gs://", "gcs://")):
                con.execute(
                    "CREATE OR REPLACE SECRET gcs (TYPE GCS, KEY_ID ?, SECRET ?)",
                    [os.environ.get("GCS_HMAC_KEY_ID", ""), os.environ.get("GCS_HMAC_SECRET", "")],
                )
            elif u.startswith(("abfss://", "az://", "azure://")):
                con.execute(
                    "CREATE OR REPLACE SECRET az (TYPE AZURE, CONNECTION_STRING ?)",
                    [os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")],
                )
        except Exception:  # noqa: BLE001 - local files need no secret
            pass

    def _scan(self) -> str:
        return _FORMATS[self.fmt].format(uri=self.uri)

    # -- Source interface --
    def introspect(self) -> Schema:
        con = self._connect()
        rows = con.execute(f"DESCRIBE SELECT * FROM {self._scan()}").fetchall()
        columns = [Column(r[0], _canonical(r[1])) for r in rows]
        return Schema(self._display, columns, display_name=self._display.replace("_", " ").title())

    def approx_distinct(self, columns: list[str]) -> dict[str, int]:
        if not columns:
            return {}
        con = self._connect()
        sel = ", ".join(f'APPROX_COUNT_DISTINCT("{c}") AS c{i}' for i, c in enumerate(columns))
        try:
            row = con.execute(f"SELECT {sel} FROM {self._scan()}").fetchone()
            return {c: int(row[i]) for i, c in enumerate(columns) if row[i] is not None}
        except Exception:  # noqa: BLE001
            return {}

    def profile(self, schema: Schema) -> dict[str, dict]:
        con = self._connect()
        scan = self._scan()
        return profile_via_sql(
            lambda sql: con.execute(sql).fetchall(), scan, lambda c: f'"{c}"', schema,
            lambda col: f"SELECT {col}, COUNT(*) AS n FROM {scan} GROUP BY {col} ORDER BY n DESC LIMIT 5")

    def power_query(self) -> str:
        if self.fmt == "parquet":
            return (
                "let\n"
                f'  // Parquet at {self.uri}\n'
                "  // Local: Parquet.Document(File.Contents(path)). Cloud: use the AzureStorage /\n"
                "  // AmazonS3 / GCS connector, then Parquet.Document on the file contents.\n"
                f'  Source = Parquet.Document(File.Contents("{self.uri}"))\n'
                "in Source"
            )
        return (
            "let\n"
            f'  // {self.fmt.title()} table at {self.uri}\n'
            f"  // Power BI reads {self.fmt.title()} best via a Fabric Lakehouse or Databricks SQL\n"
            "  // endpoint. Point the DatabricksSource/SynapseSource adapter at that endpoint,\n"
            "  // or expose this table through a Fabric shortcut and use its SQL analytics endpoint.\n"
            "  Source = null\n"
            "in Source"
        )
