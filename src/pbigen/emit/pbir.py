"""Write a complete Power BI project (PBIP + PBIR report + TMDL semantic model).

Given a finished :class:`Design`, a :class:`Schema`, and a source's Power Query, this produces a
folder Power BI Desktop can open directly: a report with a left navigation sidebar (brand strip,
stacked filters, a "how to use this report" note) and a semantic model wired to the source.

The PBIR schema versions here were pinned against Microsoft's published JSON schemas; folder and
object names are restricted to word characters and hyphens, as PBIR requires.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import re

from ..core.design import Design
from ..core.layout import (
    LOGO_ZONE_H,
    MARGIN,
    PAGE_H,
    PAGE_W,
    SIDEBAR_W,
    TITLE_H,
    pack,
)
from ..core.schema import Schema
from . import model as tmdl
from .visuals import build_shape, build_textbox, build_visual, text_run

_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
# a Power BI built-in monthly base theme the custom theme is layered on top of
_BASE_THEME = "CY24SU10"
_SAFE = re.compile(r"[^0-9A-Za-z_-]+")


def _slug(text: str, fallback: str) -> str:
    s = _SAFE.sub("-", text.strip()).strip("-")
    return s or fallback


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_project(design: Design, schema: Schema, power_query: str, out_dir: str,
                  name: str, theme: dict | None = None,
                  sidebar_color: str = "#1B1F3B", accent: str = "#FFFFFF",
                  brand: str | None = None) -> str:
    """Write the project under ``out_dir/<name>`` and return the ``.pbip`` path."""
    root = os.path.join(out_dir, name)
    report_dir = os.path.join(root, f"{name}.Report")
    model_dir = os.path.join(root, f"{name}.SemanticModel")
    defn = os.path.join(report_dir, "definition")

    _write_semantic_model(model_dir, schema, design, power_query)
    theme_file = _write_theme(defn, theme)
    _write_report_shell(report_dir, defn, theme_file)
    _write_pages(defn, design, schema, brand or schema.display_name, sidebar_color, accent)

    pbip_path = os.path.join(root, f"{name}.pbip")
    _write_json(pbip_path, {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{name}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    return pbip_path


# --------------------------------------------------------------------------- report shell
def _write_report_shell(report_dir: str, defn: str, theme_file: str | None) -> None:
    _write_json(os.path.join(report_dir, "definition.pbir"), {
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{os.path.basename(report_dir)[:-7]}.SemanticModel"}},
    })
    # Power BI Desktop requires a $schema in version.json (it errors on load without it).
    _write_json(os.path.join(defn, "version.json"), {
        "$schema": f"{_REPORT}/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })

    report: dict = {
        "$schema": f"{_REPORT}/report/1.3.0/schema.json",
        "layoutOptimization": "None",
    }
    if theme_file:
        # A custom theme is applied on top of a built-in base theme, and both the theme and the base
        # must be declared in resourcePackages — this mirrors what Power BI Desktop itself writes.
        report["themeCollection"] = {
            "baseTheme": {"name": _BASE_THEME, "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": theme_file, "reportVersionAtImport": "5.61", "type": "RegisteredResources"},
        }
        report["resourcePackages"] = [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": _BASE_THEME, "path": f"BaseThemes/{_BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}]},
        ]
        report["settings"] = {"useStylableVisualContainerHeader": True}
    _write_json(os.path.join(defn, "report.json"), report)


def _write_theme(defn: str, theme: dict | None) -> str | None:
    """Write the theme as a registered resource; return its file name (used as the customTheme name)."""
    if not theme:
        return None
    theme_file = f"{_slug(theme.get('name', 'theme'), 'theme')}.json"
    path = os.path.join(defn, "StaticResources", "RegisteredResources", theme_file)
    _write_json(path, theme)
    return theme_file


# --------------------------------------------------------------------------- semantic model
def _write_semantic_model(model_dir: str, schema: Schema, design: Design, power_query: str) -> None:
    defn = os.path.join(model_dir, "definition")
    _write_json(os.path.join(model_dir, "definition.pbism"), json.loads(tmdl.pbism()))
    _write_text(os.path.join(defn, "database.tmdl"), tmdl.database_tmdl())
    _write_text(os.path.join(defn, "model.tmdl"), tmdl.model_tmdl())
    _write_text(os.path.join(defn, "tables", f"{schema.table}.tmdl"),
                tmdl.table_tmdl(schema, design.measures, power_query))


# --------------------------------------------------------------------------- pages + visuals
def _write_pages(defn: str, design: Design, schema: Schema, brand: str,
                 sidebar_color: str, accent: str) -> None:
    pages_dir = os.path.join(defn, "pages")
    order: list[str] = []
    used: set[str] = set()

    for pi, page in enumerate(design.pages):
        pid = _unique(_slug(page.name, f"page{pi}") or f"page{pi}", used)
        order.append(pid)
        _write_json(os.path.join(pages_dir, pid, "page.json"), {
            "$schema": f"{_REPORT}/page/1.4.0/schema.json",
            "name": pid,
            "displayName": page.name,
            "displayOption": "FitToPage",
            "height": PAGE_H,
            "width": PAGE_W,
        })
        _write_page_visuals(pages_dir, pid, page, schema, design, brand, sidebar_color, accent)

    _write_json(os.path.join(pages_dir, "pages.json"), {
        "$schema": f"{_REPORT}/pagesMetadata/1.0.0/schema.json",
        "pageOrder": order,
        "activePageName": order[0] if order else "page0",
    })


def _write_page_visuals(pages_dir: str, pid: str, page, schema: Schema, design: Design,
                        brand: str, sidebar_color: str, accent: str) -> None:
    vdir = os.path.join(pages_dir, pid, "visuals")
    table = schema.table
    tab = 0

    def emit(obj: dict) -> None:
        nonlocal tab
        _write_json(os.path.join(vdir, obj["name"], "visual.json"), obj)
        tab += 1

    # sidebar background (behind everything)
    emit(build_shape(f"{pid}-nav", 0, 0, SIDEBAR_W, PAGE_H, 0, tab, sidebar_color))
    # brand strip
    emit(build_textbox(f"{pid}-brand", [text_run(brand, "20pt", bold=True, color=accent)],
                       20, 28, SIDEBAR_W - 40, LOGO_ZONE_H - 60, 1, tab, align="left"))
    # page title in the main area
    emit(build_textbox(f"{pid}-title", [text_run(page.name, "24pt", bold=True, color="#1B1F3B")],
                       SIDEBAR_W + MARGIN, MARGIN, PAGE_W - SIDEBAR_W - 2 * MARGIN, TITLE_H, 1, tab))

    placed = pack(page, schema)
    z = 2
    for i, v in enumerate(placed):
        obj = build_visual(v, table, f"{pid}-v{i:02d}", tab)
        obj["position"]["z"] = z
        z += 1
        emit(obj)

    # "how to use this report" note, pinned to the bottom of the sidebar
    if design.usage_notes:
        runs = [text_run("How to use this report\n", "12pt", bold=True, color="#000000")]
        for note in design.usage_notes[:4]:
            runs.append(text_run(f"• {note}\n", "9pt", color="#000000"))
        emit(build_textbox(f"{pid}-notes", runs, 16, PAGE_H - 320, SIDEBAR_W - 32, 300, z, tab,
                           background="#FFFFFF", align="left"))


def _unique(base: str, used: set[str]) -> str:
    name = base
    i = 1
    while name in used:
        name = f"{base}-{i}"
        i += 1
    used.add(name)
    return name
