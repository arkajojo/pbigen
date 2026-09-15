"""Cube semantic-layer source.

Cube (https://cube.dev) exposes a governed set of measures and dimensions over any warehouse
through a SQL API (Postgres wire protocol) and a REST/GraphQL API. Reading from Cube means the
generated report inherits the organisation's already-modelled metrics instead of re-deriving
them — the semantic layer stays the single source of truth.

Introspection uses Cube's ``/meta`` endpoint (measures + dimensions of a cube). Power BI connects
through Cube's SQL API using the standard PostgreSQL connector.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import urllib.request

from ..core.schema import (
    BOOLEAN,  # noqa: F401
    DATETIME,
    DECIMAL,
    STRING,
    Column,
    Schema,
)
from .base import Source

_DIM_TYPE = {
    "string": STRING, "number": DECIMAL, "boolean": BOOLEAN,
    "time": DATETIME, "geo": STRING,
}


class CubeSource(Source):
    kind = "cube"

    def __init__(self, cube: str, api_url: str | None = None, api_token: str | None = None,
                 sql_host: str | None = None, sql_port: int = 15432,
                 sql_database: str = "cube", sql_user: str | None = None,
                 sql_password: str | None = None):
        self.cube = cube
        self.api_url = (api_url or os.environ.get("CUBE_API_URL", "")).rstrip("/")
        self.api_token = api_token or os.environ.get("CUBE_API_TOKEN", "")
        self.sql_host = sql_host or os.environ.get("CUBE_SQL_HOST", "")
        self.sql_port = sql_port
        self.sql_database = sql_database
        self.sql_user = sql_user or os.environ.get("CUBE_SQL_USER", "")
        self.sql_password = sql_password or os.environ.get("CUBE_SQL_PASSWORD", "")

    def _meta(self) -> dict:
        req = urllib.request.Request(f"{self.api_url}/meta")  # noqa: S310 - user-configured endpoint
        if self.api_token:
            req.add_header("Authorization", self.api_token)
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    def introspect(self) -> Schema:
        meta = self._meta()
        cube = next((c for c in meta.get("cubes", []) if c.get("name") == self.cube), None)
        if cube is None:
            raise ValueError(f"cube {self.cube!r} not found in {self.api_url}/meta")
        columns: list[Column] = []
        for m in cube.get("measures", []):
            # measures are already-aggregated numerics in the semantic layer
            columns.append(Column(m["name"].split(".", 1)[-1], DECIMAL))
        for d in cube.get("dimensions", []):
            columns.append(Column(d["name"].split(".", 1)[-1], _DIM_TYPE.get(d.get("type"), STRING)))
        return Schema(self.cube, columns, display_name=cube.get("title") or self.cube.title())

    def approx_distinct(self, columns: list[str]) -> dict[str, int]:
        # Cube dimensions are governed; cardinality via the SQL API is optional and best-effort.
        if not (self.sql_host and columns):
            return {}
        try:
            from sqlalchemy import create_engine, text
            url = (f"postgresql+psycopg://{self.sql_user}:{self.sql_password}"
                   f"@{self.sql_host}:{self.sql_port}/{self.sql_database}")
            sel = ", ".join(f'COUNT(DISTINCT "{c}") AS c{i}' for i, c in enumerate(columns))
            with create_engine(url).connect() as conn:
                row = conn.execute(text(f'SELECT {sel} FROM "{self.cube}"')).fetchone()
            return {c: int(row[i]) for i, c in enumerate(columns) if row[i] is not None}
        except Exception:  # noqa: BLE001
            return {}

    def power_query(self) -> str:
        # Cube's SQL API speaks the PostgreSQL wire protocol.
        return (
            "let\n"
            f'  Source = PostgreSQL.Database("{self.sql_host}:{self.sql_port}", "{self.sql_database}"),\n'
            f'  Data = Source{{[Schema="public", Item="{self.cube}"]}}[Data]\n'
            "in Data"
        )
