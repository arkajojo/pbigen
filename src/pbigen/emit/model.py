"""Emit the Power BI semantic model as TMDL.

The model binds one table to the source's Power Query (M) expression, types every column, and
turns the design's logical measures into DAX. TMDL is tab-indented text; this writer keeps that
contract exactly so Power BI Desktop opens the project without repair.

Author: Arka Gupta
"""
from __future__ import annotations

from collections.abc import Iterable

from ..core.design import Measure
from ..core.schema import (
    BOOLEAN,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INTEGER,
    TIME,
    Schema,
)

_TMDL_TYPE = {
    "string": "string", INTEGER: "int64", FLOAT: "double", DECIMAL: "decimal",
    BOOLEAN: "boolean", DATE: "dateTime", DATETIME: "dateTime", TIME: "string",
}
_SUMMARIZE = {INTEGER: "sum", FLOAT: "sum", DECIMAL: "sum"}

COMPAT_LEVEL = 1567


def _dax(m: Measure, table: str, cols: set[str]) -> str:
    """DAX for a measure. Any reference to a column not in ``cols`` degrades to a safe COUNTROWS
    rather than an expression that errors the visual in Power BI."""
    agg = (m.agg or "SUM").upper()
    if m.kind == "ratio":
        if m.numerator in cols and m.denominator in cols:
            return f"DIVIDE(SUM('{table}'[{m.numerator}]), SUM('{table}'[{m.denominator}]))"
        return f"COUNTROWS('{table}')"
    col = m.column
    if not col or col not in cols:      # missing/invalid column -> would error; use a safe count
        return f"COUNTROWS('{table}')"
    return f"{agg}('{table}'[{col}])"


def _format_string(m: Measure) -> str:
    if m.percent:
        return "0.0%"
    if m.money:
        return "\\$#,0.00;(\\$#,0.00)"
    return "#,0"


def _indent(text: str, tabs: int) -> str:
    pad = "\t" * tabs
    return "\n".join(pad + line if line else line for line in text.splitlines())


def database_tmdl() -> str:
    return f"database\n\tcompatibilityLevel: {COMPAT_LEVEL}\n"


def model_tmdl() -> str:
    return (
        "model Model\n"
        "\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: en-US\n"
    )


def normalize_mode(mode: str | None) -> str:
    """Map a user storage-mode choice to the TMDL partition mode."""
    m = (mode or "import").lower().replace("-", "").replace("_", "").replace(" ", "")
    return "directQuery" if m in ("directquery", "dq", "direct") else "import"


def table_tmdl(schema: Schema, measures: Iterable[Measure], power_query: str,
               mode: str = "import") -> str:
    table = schema.table
    cols = {c.name for c in schema.columns}
    lines: list[str] = [f"table '{table}'", ""]

    for m in measures:
        lines.append(f"\tmeasure '{m.name}' = {_dax(m, table, cols)}")
        lines.append(f"\t\tformatString: {_format_string(m)}")
        lines.append("")

    for c in schema.columns:
        dtype = _TMDL_TYPE.get(c.dtype, "string")
        lines.append(f"\tcolumn '{c.name}'")
        lines.append(f"\t\tdataType: {dtype}")
        lines.append(f"\t\tsummarizeBy: {_SUMMARIZE.get(c.dtype, 'none')}")
        lines.append(f"\t\tsourceColumn: {c.name}")
        if dtype == "dateTime":
            lines.append('\t\tformatString: Long Date')
        lines.append("")

    lines.append(f"\tpartition '{table}' = m")
    lines.append(f"\t\tmode: {normalize_mode(mode)}")
    lines.append("\t\tsource =")
    lines.append(_indent(power_query, 3))
    lines.append("")
    return "\n".join(lines) + "\n"


def pbism() -> str:
    return '{\n  "version": "4.0",\n  "settings": {}\n}\n'
