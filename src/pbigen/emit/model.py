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


def _dax(m: Measure, table: str, cols: set[str], measures: set[str] | None = None) -> str:
    """DAX for a measure. Any reference to a column (or measure) that does not exist degrades to a
    safe COUNTROWS rather than an expression that errors the visual in Power BI."""
    measures = measures or set()
    agg = (m.agg or "SUM").upper()
    if m.kind == "dax" and m.expression:
        return m.expression                      # generated internally (time intelligence, labels)
    if m.kind in ("divide", "add", "subtract", "multiply"):
        if m.numerator in measures and m.denominator in measures:
            a, b = f"[{m.numerator}]", f"[{m.denominator}]"
            return {"divide": f"DIVIDE({a}, {b})", "add": f"{a} + {b}",
                    "subtract": f"{a} - {b}", "multiply": f"{a} * {b}"}[m.kind]
        return f"COUNTROWS('{table}')"
    if m.kind == "ratio":
        if m.numerator in cols and m.denominator in cols:
            return f"DIVIDE(SUM('{table}'[{m.numerator}]), SUM('{table}'[{m.denominator}]))"
        return f"COUNTROWS('{table}')"
    col = m.column
    if agg == "COUNT" and (not col or col not in cols):
        return f"COUNTROWS('{table}')"
    if not col or col not in cols:      # missing/invalid column -> would error; use a safe count
        return f"COUNTROWS('{table}')"
    return f"{agg}('{table}'[{col}])"


def _format_string(m: Measure) -> str | None:
    if m.kind == "dax" and m.hidden:
        return None                              # text / colour helper measures
    if m.percent:
        return "0.0%"
    if m.money:
        return "\\$#,0.00;(\\$#,0.00)"
    if (m.agg or "").upper() == "AVERAGE" or m.kind in ("divide", "ratio", "multiply"):
        return "#,0.00"
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
    measures = list(measures)
    cols = {c.name for c in schema.columns}
    mnames = {m.name for m in measures}
    lines: list[str] = [f"table '{table}'", ""]

    for m in measures:
        lines.append(f"\tmeasure '{_esc(m.name)}' = {_dax(m, table, cols, mnames)}")
        fmt = _format_string(m)
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        if m.hidden:
            lines.append("\t\tisHidden")
        lines.append("")

    for c in schema.columns:
        dtype = _TMDL_TYPE.get(c.dtype, "string")
        if c.expression:                                  # model-calculated column (e.g. month grain)
            lines.append(f"\tcolumn '{_esc(c.name)}' = {c.expression}")
            lines.append(f"\t\tdataType: {dtype}")
            lines.append("\t\tsummarizeBy: none")
            if dtype == "dateTime":
                lines.append("\t\tformatString: mmm yyyy")
            lines.append("")
            continue
        lines.append(f"\tcolumn '{_esc(c.name)}'")
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


def _esc(name: str) -> str:
    """Escape a TMDL quoted object name (a single quote is doubled)."""
    return name.replace("'", "''")


def pbism() -> str:
    return '{\n  "version": "4.0",\n  "settings": {}\n}\n'
