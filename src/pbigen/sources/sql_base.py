"""SQLAlchemy-backed source base.

Every warehouse with a SQLAlchemy dialect (Postgres, Redshift, Snowflake, Synapse, Databricks,
ClickHouse, Athena, …) introspects the same way: the SQLAlchemy Inspector gives typed columns,
and a single ``COUNT(DISTINCT …)`` query gives cardinality. Concrete adapters only supply a
connection URL and the Power BI (M) template for their connector.

Author: Arka Gupta
"""
from __future__ import annotations

import datetime as _dt
import decimal as _dec

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


def _canonical(sa_type) -> str:
    """Map a SQLAlchemy column type to the canonical vocabulary."""
    try:
        py = sa_type.python_type
    except (NotImplementedError, AttributeError):
        py = None
    if py is bool:
        return BOOLEAN
    if py is int:
        return INTEGER
    if py is float:
        return FLOAT
    if py is _dec.Decimal:
        return DECIMAL
    if py is _dt.datetime:
        return DATETIME
    if py is _dt.date:
        return DATE
    if py is _dt.time:
        return TIME
    name = type(sa_type).__name__.upper()
    if any(k in name for k in ("INT",)):
        return INTEGER
    if any(k in name for k in ("NUMERIC", "DECIMAL")):
        return DECIMAL
    if any(k in name for k in ("FLOAT", "REAL", "DOUBLE")):
        return FLOAT
    if "BOOL" in name:
        return BOOLEAN
    if "TIMESTAMP" in name or "DATETIME" in name:
        return DATETIME
    if "DATE" in name:
        return DATE
    return STRING


class SqlSource(Source):
    """Introspect any SQLAlchemy-addressable table. Subclasses set ``url`` + ``power_query``."""

    kind = "sql"

    def __init__(self, url: str, table: str, schema: str | None = None,
                 quote: str = '"', connect_args: dict | None = None):
        self.url = url
        self.table = table
        self.db_schema = schema
        self._quote = quote
        self._connect_args = connect_args or {}
        self._engine = None

    # -- engine (lazy so importing the adapter never requires a live connection) --
    def _get_engine(self):
        if self._engine is None:
            from sqlalchemy import create_engine
            self._engine = create_engine(self.url, connect_args=self._connect_args)
        return self._engine

    def _q(self, ident: str) -> str:
        return f"{self._quote}{ident}{self._quote}"

    def _qualified(self) -> str:
        return f"{self._q(self.db_schema)}.{self._q(self.table)}" if self.db_schema else self._q(self.table)

    # -- Source interface --
    def introspect(self) -> Schema:
        from sqlalchemy import inspect
        insp = inspect(self._get_engine())
        cols = insp.get_columns(self.table, schema=self.db_schema)
        columns = [Column(c["name"], _canonical(c["type"])) for c in cols]
        return Schema(self.table, columns, display_name=self.table.replace("_", " ").title())

    def approx_distinct(self, columns: list[str]) -> dict[str, int]:
        if not columns:
            return {}
        from sqlalchemy import text
        # portable across dialects; adapters may override with APPROX_COUNT_DISTINCT for scale
        sel = ", ".join(f"COUNT(DISTINCT {self._q(c)}) AS c{i}" for i, c in enumerate(columns))
        sql = f"SELECT {sel} FROM {self._qualified()}"
        try:
            with self._get_engine().connect() as conn:
                row = conn.execute(text(sql)).fetchone()
            return {c: int(row[i]) for i, c in enumerate(columns) if row[i] is not None}
        except Exception:  # noqa: BLE001 - cardinality is best-effort, never fatal
            return {}

    def profile(self, schema: Schema) -> dict[str, dict]:
        from sqlalchemy import text

        def run(sql: str):
            with self._get_engine().connect() as conn:
                return conn.execute(text(sql)).fetchall()

        qual = self._qualified()
        return profile_via_sql(run, qual, self._q, schema, lambda col: self._top_values_sql(col, qual))

    def _top_values_sql(self, col: str, qual: str) -> str:
        return f"SELECT {col}, COUNT(*) AS n FROM {qual} GROUP BY {col} ORDER BY n DESC LIMIT 5"

    def power_query(self) -> str:
        raise NotImplementedError
