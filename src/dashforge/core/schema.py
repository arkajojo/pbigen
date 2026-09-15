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

    def names(self) -> list[str]:
        return [c.name for c in self.columns]

    def by_name(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)

    def with_cardinality(self, counts: dict[str, int]) -> Schema:
        """Return a copy with distinct-value counts merged onto matching columns."""
        cols = [
            Column(c.name, c.dtype, counts.get(c.name, c.cardinality)) for c in self.columns
        ]
        return Schema(self.table, cols, self.display_name)
