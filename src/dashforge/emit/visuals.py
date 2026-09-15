"""Build PBIR ``visual.json`` objects (visualContainer/2.0.0).

Each logical :class:`~dashforge.core.design.Visual` becomes a Power BI visual container with its
field bindings expressed as query projections. Measures bind by name to model measures; category /
series / column roles bind to model columns. Styling is left to the theme, so these objects stay
minimal and schema-clean.

Author: Arka Gupta
"""
from __future__ import annotations

from typing import Any

from ..core.design import Visual

VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
    "visualContainer/2.0.0/schema.json"
)

# logical type -> Power BI built-in visualType
_VISUAL_TYPE = {
    "card": "card", "kpi": "card",
    "line": "lineChart", "area": "areaChart",
    "column": "clusteredColumnChart", "columnStacked": "columnChart",
    "bar": "clusteredBarChart", "barStacked": "barChart",
    "donut": "donutChart", "pie": "pieChart", "scatter": "scatterChart",
    "table": "tableEx", "matrix": "pivotTable", "slicer": "slicer",
}


def _lit(value: Any) -> dict:
    """Wrap a literal for a PBIR formatting-object property."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = f"'{value}'"
    return {"expr": {"Literal": {"Value": v}}}


def _proj_measure(table: str, name: str) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": name,
    }


def _proj_column(table: str, name: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": name,
    }


def _query_state(v: Visual, table: str) -> dict:
    """Map a visual's roles to the projection buckets Power BI expects for its type."""
    m = [_proj_measure(table, name) for name in v.measures]
    state: dict[str, dict] = {}

    def put(role: str, projs: list[dict]) -> None:
        if projs:
            state[role] = {"projections": projs}

    t = v.type
    if t in ("card", "kpi"):
        put("Values", m)
    elif t in ("line", "area", "column", "columnStacked", "bar", "barStacked"):
        put("Category", [_proj_column(table, v.category)] if v.category else [])
        put("Y", m)
        put("Series", [_proj_column(table, v.series)] if v.series else [])
    elif t in ("donut", "pie"):
        put("Category", [_proj_column(table, v.category)] if v.category else [])
        put("Y", m)
    elif t == "scatter":
        put("X", [_proj_measure(table, v.x_measure)] if v.x_measure else m[:1])
        put("Y", [_proj_measure(table, v.y_measure)] if v.y_measure else m[1:2])
        put("Size", [_proj_measure(table, v.size_measure)] if v.size_measure else [])
        put("Category", [_proj_column(table, v.category)] if v.category else [])
    elif t == "table":
        cols = [_proj_column(table, c) for c in v.columns] + m
        put("Values", cols)
    elif t == "matrix":
        put("Rows", [_proj_column(table, v.category)] if v.category else [])
        put("Columns", [_proj_column(table, v.series)] if v.series else [])
        put("Values", m)
    elif t == "slicer":
        put("Values", [_proj_column(table, v.category)] if v.category else [])
    return state


def _title_objects(title: str) -> dict:
    return {"title": [{"properties": {
        "show": _lit(True),
        "text": _lit(title),
    }}]}


def build_visual(v: Visual, table: str, name: str, tab_order: int) -> dict:
    visual_type = _VISUAL_TYPE.get(v.type, "tableEx")
    obj: dict[str, Any] = {}

    if v.type == "slicer":
        data_props: dict[str, Any] = {"mode": _lit(v.slicer_mode)}
        obj["data"] = [{"properties": data_props}]
        obj["header"] = [{"properties": {"show": _lit(True), "text": _lit(v.title or v.category or "")}}]
    elif v.title and v.type not in ("card", "kpi"):
        obj.update(_title_objects(v.title))

    visual: dict[str, Any] = {"visualType": visual_type, "drillFilterOtherVisuals": True}
    qs = _query_state(v, table)
    if qs:
        visual["query"] = {"queryState": qs}
    if obj:
        visual["objects"] = obj

    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {
            "x": float(v.x), "y": float(v.y), "z": float(v.z),
            "width": float(v.w), "height": float(v.h), "tabOrder": tab_order,
        },
        "visual": visual,
    }


def build_textbox(name: str, runs: list[dict], x: int, y: int, w: int, h: int,
                  z: int, tab_order: int, background: str | None = None,
                  align: str = "left") -> dict:
    """A textbox visual (used for the page title and the 'how to use' notes)."""
    paragraphs = [{"textRuns": runs, "horizontalTextAlignment": align}]
    objects: dict[str, Any] = {"general": [{"properties": {"paragraphs": paragraphs}}]}
    if background:
        objects["background"] = [{"properties": {"show": _lit(True),
                                                 "color": {"solid": {"color": _lit(background)}}}}]
        objects["border"] = [{"properties": {"show": _lit(False)}}]
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": {"visualType": "textbox", "drillFilterOtherVisuals": True, "objects": objects},
    }


def build_shape(name: str, x: int, y: int, w: int, h: int, z: int, tab_order: int,
                fill: str) -> dict:
    """A filled rectangle — the left navigation sidebar background."""
    objects = {
        "shape": [{"properties": {"tileShape": _lit("rectangle")}}],
        "fill": [{"properties": {"show": _lit(True), "fillColor": {"solid": {"color": _lit(fill)}}}}],
        "outline": [{"properties": {"show": _lit(False)}}],
    }
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": {"visualType": "shape", "drillFilterOtherVisuals": False, "objects": objects},
    }


def text_run(value: str, size: str | None = None, bold: bool = False,
             color: str | None = None) -> dict:
    style: dict[str, Any] = {}
    if size:
        style["fontSize"] = size
    if bold:
        style["fontWeight"] = "bold"
    if color:
        style["color"] = color
    run: dict[str, Any] = {"value": value}
    if style:
        run["textStyle"] = style
    return run
