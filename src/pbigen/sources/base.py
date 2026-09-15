"""The Source contract.

A source does three jobs at generation time:

1. **introspect()**  -> the table's :class:`Schema` (columns + canonical types).
2. **approx_distinct()** -> distinct-value counts, so the design can pick data-appropriate
   charts and filters (a 1000-value date becomes a range slider, not a dropdown).
3. **power_query()** -> the Power Query (M) expression the generated Power BI model uses to
   connect back to this source at refresh time.

Introspection reads *metadata only* — never row data — and every adapter is read-only.

Author: Arka Gupta
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

from ..core.schema import Schema


@dataclass
class ConnectionTest:
    ok: bool
    message: str


class Source(abc.ABC):
    """Base class for every data source adapter."""

    #: short identifier used in the registry and CLI, e.g. "bigquery"
    kind: str = "source"

    @abc.abstractmethod
    def introspect(self) -> Schema:
        """Return the columns (with canonical types) of the configured table/view."""

    @abc.abstractmethod
    def approx_distinct(self, columns: list[str]) -> dict[str, int]:
        """Return approximate distinct counts for ``columns`` (best-effort; may be empty)."""

    @abc.abstractmethod
    def power_query(self) -> str:
        """Return the Power Query (M) ``let … in …`` expression for the semantic model."""

    def test_connection(self) -> ConnectionTest:
        """Verify the source is reachable and the table is introspectable."""
        try:
            schema = self.introspect()
            n = len(schema.columns)
            if n == 0:
                return ConnectionTest(False, f"connected but no columns found for {self.kind}")
            return ConnectionTest(True, f"{self.kind}: OK — {n} columns in {schema.table}")
        except Exception as exc:  # noqa: BLE001 - surface any driver/auth error verbatim
            return ConnectionTest(False, f"{self.kind}: {type(exc).__name__}: {exc}")

    def schema_with_cardinality(self) -> Schema:
        """Introspect and merge distinct counts in one step (used by the generator)."""
        schema = self.introspect()
        # only bother counting columns that could be dimensions/filters (not pure measures)
        candidates = [c.name for c in schema.columns if c.dtype in ("string", "date", "datetime", "boolean", "integer")]
        counts = self.approx_distinct(candidates[:24]) if candidates else {}
        return schema.with_cardinality(counts)
