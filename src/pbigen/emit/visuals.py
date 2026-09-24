"""Build PBIR ``visual.json`` objects (visualContainer/2.0.0).

Each logical :class:`~pbigen.core.design.Visual` becomes a Power BI visual container with its
field bindings expressed as query projections. Measures bind by name to model measures; category /
series / column roles bind to model columns. Colours and fonts come from the theme; on top of
that each visual gets:

* a themed **title** and a **subtitle** that says how to read it (stylable container header),
* KPI cards with a **period-over-period delta** in the subtitle, coloured by a measure
  (green when the change is good for that KPI, red when bad),
* **ranked** category charts (sorted by the measure, descending) and data labels where useful,
* optional **template styles** — formatting harvested from a customer's report, merged under
  pbigen's own bindings so their look carries over without their data.

Author: Arka Gupta
"""
from __future__ import annotations

import copy
from typing import Any

from ..core.design import Visual

VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
    "visualContainer/2.0.0/schema.json"
)

# logical type -> Power BI built-in visualType
VISUAL_TYPE = {
    "card": "card", "kpi": "card",
    "line": "lineChart", "area": "areaChart",
    "column": "clusteredColumnChart", "columnStacked": "columnChart",
    "bar": "clusteredBarChart", "barStacked": "barChart",
    "combo": "lineClusteredColumnComboChart", "waterfall": "waterfallChart",
    "donut": "donutChart", "pie": "pieChart", "treemap": "treemap", "scatter": "scatterChart",
    "table": "tableEx", "matrix": "pivotTable", "slicer": "slicer",
}
_VISUAL_TYPE = VISUAL_TYPE  # backwards-compatible alias

_RANKABLE = {"bar", "column", "barStacked", "columnStacked", "donut", "pie", "treemap", "waterfall"}


def _lit(value: Any) -> dict:
    """Wrap a literal for a PBIR formatting-object property."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def _measure_field(table: str, name: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def _measure_expr(table: str, name: str) -> dict:
    """A formatting property bound to a measure's value (Power BI "fx" / field value)."""
    return {"expr": _measure_field(table, name)}


def _proj_measure(table: str, name: str) -> dict:
    return {
        "field": _measure_field(table, name),
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

    cat = [_proj_column(table, v.category)] if v.category else []
    ser = [_proj_column(table, v.series)] if v.series else []
    t = v.type
    if t in ("card", "kpi"):
        put("Values", m[:1])
    elif t in ("line", "area", "column", "columnStacked", "bar", "barStacked"):
        put("Category", cat)
        put("Y", m)
        put("Series", ser)
    elif t == "combo":
        put("Category", cat)
        put("Y", m)
        put("Y2", [_proj_measure(table, n) for n in v.line_measures])
    elif t == "waterfall":
        put("Category", cat)
        put("Y", m[:1])
        put("Breakdown", ser)
    elif t in ("donut", "pie"):
        put("Category", cat)
        put("Y", m[:1])
    elif t == "treemap":
        put("Group", cat)
        put("Details", ser)
        put("Values", m[:1])
    elif t == "scatter":
        put("X", [_proj_measure(table, v.x_measure)] if v.x_measure else m[:1])
        put("Y", [_proj_measure(table, v.y_measure)] if v.y_measure else m[1:2])
        put("Size", [_proj_measure(table, v.size_measure)] if v.size_measure else [])
        put("Category", cat)
    elif t == "table":
        put("Values", [_proj_column(table, c) for c in v.columns] + m)
    elif t == "matrix":
        put("Rows", cat)
        put("Columns", ser)
        put("Values", m)
    elif t == "slicer":
        put("Values", cat)
    return state


# The stylable visual-container header (enabled in report.json) shows a title bar. Charts want a
# themed title there; chrome (textboxes, shapes, slicers) must hide it, or an empty white header
# renders on top of them.
def _container_title(title: str) -> dict:
    return {"title": [{"properties": {"show": _lit(True), "text": _lit(title)}}]}


def _container_no_title() -> dict:
    return {"title": [{"properties": {"show": _lit(False)}}]}


def _merge_objects(base: dict, style: dict | None) -> dict:
    """Merge template formatting (``style``) under pbigen's own objects (``base`` wins)."""
    if not style:
        return base
    out = copy.deepcopy(style)
    for key, entries in base.items():
        if key in out and out[key] and entries:
            props = dict(out[key][0].get("properties", {}))
            props.update(entries[0].get("properties", {}))
            out[key] = [{**entries[0], "properties": props}] + list(entries[1:])
        else:
            out[key] = entries
    return out


def build_visual(v: Visual, table: str, name: str, tab_order: int,
                 style: dict | None = None) -> dict:
    """A data visual. ``style`` = ``{"objects": {...}, "visualContainerObjects": {...}}`` from a
    template pack, applied beneath pbigen's bindings."""
    visual_type = VISUAL_TYPE.get(v.type, "tableEx")
    obj: dict[str, Any] = {}

    if v.type == "slicer":
        obj["data"] = [{"properties": {"mode": _lit(v.slicer_mode)}}]
        obj["header"] = [{"properties": {"show": _lit(True), "text": _lit(v.title or v.category or "")}}]
        vco = _container_no_title()
    elif v.type in ("card", "kpi"):
        # title = KPI name; big number in the middle; subtitle = coloured period delta
        obj["categoryLabels"] = [{"properties": {"show": _lit(False)}}]
        vco = _container_title(v.title or (v.measures[0] if v.measures else ""))
        if v.delta_label:
            sub: dict[str, Any] = {"show": _lit(True), "text": _measure_expr(table, v.delta_label)}
            if v.delta_color:
                sub["fontColor"] = {"solid": {"color": _measure_expr(table, v.delta_color)}}
            vco["subTitle"] = [{"properties": sub}]
    elif not v.title:
        vco = _container_no_title()
    else:
        vco = _container_title(v.title)     # the theme's `title` style colours this
        if v.subtitle:
            vco["subTitle"] = [{"properties": {"show": _lit(True), "text": _lit(v.subtitle)}}]

    if v.labels and v.type not in ("card", "kpi", "slicer", "table", "matrix"):
        obj["labels"] = [{"properties": {"show": _lit(True)}}]

    visual: dict[str, Any] = {"visualType": visual_type, "drillFilterOtherVisuals": True}
    qs = _query_state(v, table)
    if qs:
        visual["query"] = {"queryState": qs}
        if v.sort_desc and v.type in _RANKABLE and v.measures:
            visual["query"]["sortDefinition"] = {
                "sort": [{"field": _measure_field(table, v.measures[0]), "direction": "Descending"}],
                "isDefaultSort": False,
            }
    style = style or {}
    obj = _merge_objects(obj, style.get("objects"))
    vco = _merge_objects(vco, style.get("visualContainerObjects"))
    if obj:
        visual["objects"] = obj
    visual["visualContainerObjects"] = vco

    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {
            "x": float(v.x), "y": float(v.y), "z": float(v.z),
            "width": float(v.w), "height": float(v.h), "tabOrder": tab_order,
        },
        "visual": visual,
    }


def build_textbox(name: str, runs: list[dict] | list[list[dict]], x: int, y: int, w: int, h: int,
                  z: int, tab_order: int, background: str | None = None,
                  align: str = "left") -> dict:
    """A textbox visual. ``runs`` is one paragraph's runs, or a list of paragraphs' runs."""
    paras = runs if runs and isinstance(runs[0], list) else [runs]
    paragraphs = [{"textRuns": p, "horizontalTextAlignment": align} for p in paras]
    objects: dict[str, Any] = {"general": [{"properties": {"paragraphs": paragraphs}}]}
    if background:
        objects["background"] = [{"properties": {"show": _lit(True),
                                                 "color": {"solid": {"color": _lit(background)}}}}]
    else:
        # transparent — so the sidebar / canvas shows through instead of the theme's white fill
        objects["background"] = [{"properties": {"show": _lit(False)}}]
    objects["border"] = [{"properties": {"show": _lit(False)}}]
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": {"visualType": "textbox", "drillFilterOtherVisuals": True,
                   "objects": objects,
                   "visualContainerObjects": {**_container_no_title(),
                                              "dropShadow": [{"properties": {"show": _lit(False)}}]}},
    }


def build_shape(name: str, x: int, y: int, w: int, h: int, z: int, tab_order: int,
                fill: str, radius: int = 0) -> dict:
    """A filled rectangle — sidebar background, canvas, accent bars, section panels."""
    objects = {
        "shape": [{"properties": {"tileShape": _lit("rectangleRounded" if radius else "rectangle")}}],
        "fill": [{"properties": {"show": _lit(True), "fillColor": {"solid": {"color": _lit(fill)}}}}],
        "outline": [{"properties": {"show": _lit(False)}}],
    }
    if radius:
        objects["shape"][0]["properties"]["roundEdge"] = _lit(radius)
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": {"visualType": "shape", "drillFilterOtherVisuals": False,
                   "objects": objects,
                   "visualContainerObjects": {**_container_no_title(),
                                              "dropShadow": [{"properties": {"show": _lit(False)}}],
                                              "border": [{"properties": {"show": _lit(False)}}],
                                              "background": [{"properties": {"show": _lit(False)}}]}},
    }


def build_image(name: str, item_name: str, x: int, y: int, w: int, h: int,
                z: int, tab_order: int) -> dict:
    """An image visual bound to a registered resource (e.g. a logo)."""
    objects = {"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
        "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": item_name}}}}}],
        "imageScaling": [{"properties": {"imageScalingType": _lit("Fit")}}]}
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": {"visualType": "image", "drillFilterOtherVisuals": False,
                   "objects": objects,
                   "visualContainerObjects": {**_container_no_title(),
                                              "dropShadow": [{"properties": {"show": _lit(False)}}],
                                              "border": [{"properties": {"show": _lit(False)}}],
                                              "background": [{"properties": {"show": _lit(False)}}]}},
    }


def build_raw(name: str, visual_type: str, x: int, y: int, w: int, h: int, z: int,
              tab_order: int, objects: dict | None = None, vco: dict | None = None) -> dict:
    """A chrome visual carried over from a template (shape, image, page navigator …)."""
    visual: dict[str, Any] = {"visualType": visual_type, "drillFilterOtherVisuals": False}
    if objects:
        visual["objects"] = objects
    visual["visualContainerObjects"] = vco or _container_no_title()
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": float(x), "y": float(y), "z": float(z),
                     "width": float(w), "height": float(h), "tabOrder": tab_order},
        "visual": visual,
    }


def text_run(value: str, size: str | None = None, bold: bool = False,
             color: str | None = None, font: str | None = None) -> dict:
    style: dict[str, Any] = {}
    if size:
        style["fontSize"] = size
    if bold:
        style["fontWeight"] = "bold"
    if color:
        style["color"] = color
    if font:
        style["fontFamily"] = font
    run: dict[str, Any] = {"value": value}
    if style:
        run["textStyle"] = style
    return run
