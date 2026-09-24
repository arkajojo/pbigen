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

    def profile(self, schema: Schema) -> dict[str, dict]:
        """Aggregate value profile (min/max/avg, date range, top values) — opt-in via ``--profile``.

        Best-effort; adapters that can't profile return ``{}``. Never returns row-level data."""
        return {}

    def schema_with_cardinality(self) -> Schema:
        """Introspect and merge distinct counts in one step (used by the generator)."""
        schema = self.introspect()
        # only bother counting columns that could be dimensions/filters (not pure measures)
        candidates = [c.name for c in schema.columns if c.dtype in ("string", "date", "datetime", "boolean", "integer")]
        counts = self.approx_distinct(candidates[:24]) if candidates else {}
        return schema.with_cardinality(counts)


def profile_targets(schema: Schema, limit: int = 24) -> tuple[list[str], list[str], list[str]]:
    """(numeric, date, low-cardinality category) columns worth profiling."""
    num = [c.name for c in schema.source_columns() if c.is_numeric][:limit]
    dates = [c.name for c in schema.source_columns() if c.dtype in ("date", "datetime")][:4]
    cats = [c.name for c in schema.source_columns()
            if c.dtype == "string" and c.cardinality is not None and c.cardinality <= 50][:10]
    return num, dates, cats


def profile_via_sql(run, qualified: str, q, schema: Schema, top_sql) -> dict[str, dict]:
    """Generic SQL profiler. ``run(sql) -> list[tuple]``; ``q`` quotes an identifier;
    ``top_sql(col_sql) -> str`` returns a top-5 values query for one column."""
    num, dates, cats = profile_targets(schema)
    out: dict[str, dict] = {}
    parts, keys = [], []
    for c in num:
        parts += [f"MIN({q(c)})", f"MAX({q(c)})", f"AVG({q(c)})"]
        keys.append((c, ("min", "max", "avg")))
    for c in dates:
        parts += [f"MIN({q(c)})", f"MAX({q(c)})"]
        keys.append((c, ("min", "max")))
    if parts:
        try:
            row = run(f"SELECT {', '.join(parts)} FROM {qualified}")[0]
            i = 0
            for c, fields in keys:
                prof = {}
                for f in fields:
                    v = row[i]
                    i += 1
                    if v is not None:
                        prof[f] = round(v, 4) if isinstance(v, float) else (v if isinstance(v, (int, str)) else str(v))
                out[c] = prof
        except Exception:  # noqa: BLE001 - profiling is best-effort
            pass
    for c in cats:
        try:
            rows = run(top_sql(q(c)))
            out.setdefault(c, {})["top_values"] = [str(r[0]) for r in rows[:5]]
        except Exception:  # noqa: BLE001
            continue
    return out
