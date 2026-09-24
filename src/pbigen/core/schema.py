"""Canonical, source-agnostic schema types.

Every data source adapter normalises its native metadata into these types, so the design
engine and the Power BI emitter never need to know which warehouse the data came from.

Author: Arka Gupta
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Canonical data-type vocabulary. Adapters map their native types onto these; the design
# engine reasons in these terms and the emitter maps them to the target BI model types.
STRING = "string"
INTEGER = "integer"
FLOAT = "float"
DECIMAL = "decimal"
BOOLEAN = "boolean"
DATE = "date"
DATETIME = "datetime"
TIME = "time"

NUMERIC_TYPES = frozenset({INTEGER, FLOAT, DECIMAL})
TEMPORAL_TYPES = frozenset({DATE, DATETIME, TIME})


@dataclass(frozen=True)
class Column:
    """A single column of a table/view, in canonical terms."""

    name: str
    dtype: str = STRING
    #: approximate distinct-value count, when the source could cheaply provide it
    cardinality: int | None = None
    #: DAX expression for a model-calculated column (e.g. a monthly grain); None = a source column
    expression: str | None = None

    @property
    def is_numeric(self) -> bool:
        return self.dtype in NUMERIC_TYPES

    @property
    def is_temporal(self) -> bool:
        return self.dtype in TEMPORAL_TYPES


@dataclass
class Schema:
    """The shape of a table/view plus a human label used for titles."""

    table: str
    columns: list[Column] = field(default_factory=list)
    display_name: str | None = None
    #: optional aggregate profile per column (min/max/top values) — only with ``--profile``
    profile: dict[str, dict] = field(default_factory=dict)

    def names(self) -> list[str]:
        return [c.name for c in self.columns]

    def by_name(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)

    def with_cardinality(self, counts: dict[str, int]) -> Schema:
        """Return a copy with distinct-value counts merged onto matching columns."""
        cols = [
            Column(c.name, c.dtype, counts.get(c.name, c.cardinality), c.expression)
            for c in self.columns
        ]
        return Schema(self.table, cols, self.display_name, dict(self.profile))

    def source_columns(self) -> list[Column]:
        """Columns that come from the source (not model-calculated)."""
        return [c for c in self.columns if c.expression is None]


def month_column_name(date_col: str) -> str:
    return f"{date_col} Month"


def with_time_grain(schema: Schema, date_col: str | None, mode: str = "import") -> Schema:
    """Add a calculated monthly grain for ``date_col`` so trends plot by month, not by timestamp.

    Import mode only: a DAX calculated column is always valid there. In DirectQuery the raw date
    is kept (calculated columns fold differently per source)."""
    if not date_col or str(mode).lower().startswith("direct"):
        return schema
    col = schema.by_name(date_col)
    if col is None or col.dtype not in (DATE, DATETIME):
        return schema
    name = month_column_name(date_col)
    if schema.by_name(name):
        return schema
    t = schema.table
    expr = f"DATE(YEAR('{t}'[{date_col}]), MONTH('{t}'[{date_col}]), 1)"
    cols = [*schema.columns, Column(name, DATE, None, expr)]
    return Schema(schema.table, cols, schema.display_name, dict(schema.profile))
