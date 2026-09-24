"""Write a complete Power BI project (PBIP + PBIR report + TMDL semantic model).

Given a finished :class:`Design`, a :class:`Schema`, and a source's Power Query, this produces a
folder Power BI Desktop can open directly. The page shell is either:

* pbigen's own — light canvas, navigation sidebar (brand/logo, stacked filters, "how to use"),
  a header with the page title and its headline question; or
* a **template pack** — the canvas, background, chrome, title style and per-visual formatting of
  the customer's own report, with the new visuals laid into its content region.

Every project also gets an "About this report" page (when the design has one) and a
``DESIGN.md`` explaining the business context, objectives, KPI tree and storyline.

The PBIR schema versions here were pinned against Microsoft's published JSON schemas; folder and
object names are restricted to word characters and hyphens, as PBIR requires.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import re
import shutil
from typing import TYPE_CHECKING

from ..core.design import Design, Page
from ..core.layout import Frame, Rect, default_frame, pack, page_height
from ..core.schema import Schema
from . import model as tmdl
from .brief import render_design_md
from .visuals import (
    VISUAL_TYPE,
    build_image,
    build_raw,
    build_shape,
    build_textbox,
    build_visual,
    text_run,
)

if TYPE_CHECKING:
    from ..template.pack import TemplatePack

_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
# a Power BI built-in monthly base theme the custom theme is layered on top of
_BASE_THEME = "CY24SU10"
# a light neutral canvas so white cards read as raised, executive-style panels
_CANVAS = "#F2F3F7"
_DEFAULT_DATA_COLORS = ["#4C6FFF", "#22C1C3", "#FDBB2D", "#F6416C", "#7B5CFF", "#00B8A9"]
_INK, _MUTED = "#101828", "#475467"
_SAFE = re.compile(r"[^0-9A-Za-z_-]+")


def _slug(text: str, fallback: str) -> str:
    s = _SAFE.sub("-", text.strip()).strip("-")
    return s or fallback


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_project(design: Design, schema: Schema, power_query: str, out_dir: str,
                  name: str, theme: dict | None = None,
                  sidebar_color: str = "#1B1F3B", accent: str = "#FFFFFF",
                  brand: str | None = None, mode: str = "import",
                  nav_side: str = "left", logo: str | None = None,
                  canvas: str = _CANVAS, template: TemplatePack | None = None) -> str:
    """Write the project under ``out_dir/<name>`` and return the ``.pbip`` path."""
    root = os.path.join(out_dir, name)
    report_dir = os.path.join(root, f"{name}.Report")
    model_dir = os.path.join(root, f"{name}.SemanticModel")
    defn = os.path.join(report_dir, "definition")

    _write_semantic_model(model_dir, schema, design, power_query, mode)
    theme_file = _write_theme(report_dir, theme)
    logo_item = _write_logo(report_dir, logo)
    images = _write_template_assets(report_dir, template)
    _write_report_shell(report_dir, defn, theme_file, [i for i in [logo_item, *images] if i])
    data_colors = (theme or {}).get("dataColors") or _DEFAULT_DATA_COLORS
    ink = (theme or {}).get("foreground") or _INK
    shell = _Shell(schema, design, brand or schema.display_name or schema.table, sidebar_color,
                   data_colors, nav_side, logo_item, canvas, template, ink)
    _write_pages(defn, shell)

    pbip_path = os.path.join(root, f"{name}.pbip")
    _write_json(pbip_path, {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{name}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    _write_text(os.path.join(root, "DESIGN.md"), render_design_md(design, schema, name))
    return pbip_path


def _write_logo(report_dir: str, logo: str | None) -> str | None:
    """Copy a logo image into RegisteredResources; return its registered file name."""
    if not logo or not os.path.exists(logo):
        return None
    ext = os.path.splitext(logo)[1].lower() or ".png"
    item = _slug(os.path.splitext(os.path.basename(logo))[0], "logo") + ext
    dst = os.path.join(report_dir, "StaticResources", "RegisteredResources", item)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(logo, dst)
    return item


def _write_template_assets(report_dir: str, template: TemplatePack | None) -> list[str]:
    """Copy the images a template's background/chrome reference, keeping their registered names."""
    if template is None:
        return []
    from ..template.pack import referenced_images
    out = []
    for item in sorted(referenced_images(template)):
        src = template.asset_path(item)
        if os.path.exists(src):
            dst = os.path.join(report_dir, "StaticResources", "RegisteredResources", item)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            out.append(item)
    return out


# --------------------------------------------------------------------------- report shell
def _write_report_shell(report_dir: str, defn: str, theme_file: str | None,
                        images: list[str] | None = None) -> None:
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
        # keep the stylable header on so per-visual titles/subtitles (set below) take effect
        "settings": {"useStylableVisualContainerHeader": True},
    }
    packages: list[dict] = []
    registered: list[dict] = []
    if theme_file:
        # A custom theme is applied on top of a built-in base theme, and both the theme and the base
        # must be declared in resourcePackages — this mirrors what Power BI Desktop itself writes.
        report["themeCollection"] = {
            "baseTheme": {"name": _BASE_THEME, "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": theme_file, "reportVersionAtImport": "5.61", "type": "RegisteredResources"},
        }
        packages.append({"name": "SharedResources", "type": "SharedResources",
                         "items": [{"name": _BASE_THEME, "path": f"BaseThemes/{_BASE_THEME}.json", "type": "BaseTheme"}]})
        registered.append({"name": theme_file, "path": theme_file, "type": "CustomTheme"})
    for item in images or []:
        registered.append({"name": item, "path": item, "type": "Image"})
    if registered:
        packages.append({"name": "RegisteredResources", "type": "RegisteredResources", "items": registered})
    if packages:
        report["resourcePackages"] = packages
    _write_json(os.path.join(defn, "report.json"), report)


def _write_theme(report_dir: str, theme: dict | None) -> str | None:
    """Write the theme as a registered resource; return its file name (used as the customTheme name).

    The resource folder is ``<name>.Report/StaticResources/...`` — a sibling of ``definition/``, NOT
    inside it. Placing it under ``definition/`` means Power BI can't resolve it and silently falls
    back to the default theme.
    """
    if not theme:
        return None
    theme_file = f"{_slug(theme.get('name', 'theme'), 'theme')}.json"
    path = os.path.join(report_dir, "StaticResources", "RegisteredResources", theme_file)
    _write_json(path, theme)
    return theme_file


# --------------------------------------------------------------------------- semantic model
def _write_semantic_model(model_dir: str, schema: Schema, design: Design, power_query: str,
                          mode: str = "import") -> None:
    defn = os.path.join(model_dir, "definition")
    _write_json(os.path.join(model_dir, "definition.pbism"), json.loads(tmdl.pbism()))
    _write_text(os.path.join(defn, "database.tmdl"), tmdl.database_tmdl())
    _write_text(os.path.join(defn, "model.tmdl"), tmdl.model_tmdl())
    _write_text(os.path.join(defn, "tables", f"{schema.table}.tmdl"),
                tmdl.table_tmdl(schema, design.measures, power_query, mode))


# --------------------------------------------------------------------------- pages + visuals
class _Shell:
    """Everything a page needs to render its shell (default sidebar, or a template)."""

    def __init__(self, schema: Schema, design: Design, brand: str, sidebar_color: str,
                 data_colors: list[str], nav_side: str, logo_item: str | None, canvas: str,
                 template: TemplatePack | None, ink: str):
        self.schema, self.design, self.brand = schema, design, brand
        self.sidebar_color, self.data_colors = sidebar_color, data_colors
        self.nav_side, self.logo_item, self.canvas = nav_side, logo_item, canvas
        self.template, self.ink = template, ink
        self.frame: Frame = template.frame() if template else default_frame(nav_side)


def _write_pages(defn: str, shell: _Shell) -> None:
    pages_dir = os.path.join(defn, "pages")
    order: list[str] = []
    used: set[str] = set()

    for pi, page in enumerate(shell.design.pages):
        pid = _unique(_slug(page.name, f"page{pi}") or f"page{pi}", used)
        order.append(pid)
        visuals, height = _page_visuals(pid, page, shell)
        page_obj: dict = {
            "$schema": f"{_REPORT}/page/1.4.0/schema.json",
            "name": pid,
            "displayName": page.name,
            "displayOption": "FitToPage" if height <= shell.frame.page_h else "FitToWidth",
            "height": height,
            "width": shell.frame.page_w,
        }
        if shell.template and shell.template.page_objects:
            page_obj["objects"] = shell.template.page_objects
        _write_json(os.path.join(pages_dir, pid, "page.json"), page_obj)
        for obj in visuals:
            _write_json(os.path.join(pages_dir, pid, "visuals", obj["name"], "visual.json"), obj)

    _write_json(os.path.join(pages_dir, "pages.json"), {
        "$schema": f"{_REPORT}/pagesMetadata/1.0.0/schema.json",
        "pageOrder": order,
        "activePageName": order[0] if order else "page0",
    })


def _page_visuals(pid: str, page: Page, shell: _Shell) -> tuple[list[dict], int]:
    """All visual.json objects for a page, plus the page height it needs."""
    frame, table = shell.frame, shell.schema.table
    out: list[dict] = []
    z = 0

    def add(obj: dict) -> None:
        nonlocal z
        obj["position"]["z"] = float(z)
        obj["position"]["tabOrder"] = len(out)
        out.append(obj)
        z += 1

    # lay the page out first: its height decides how tall the shell background must be
    if page.kind == "about":
        placed = []
        body = _about_boxes(pid, page, frame, shell)
        height = max(frame.page_h, max((int(b["position"]["y"] + b["position"]["height"]) for b in body),
                                       default=0) + 28)
    else:
        placed = pack(page, shell.schema, shell.nav_side, frame)
        body = []
        height = page_height(placed, frame)

    # ---- shell ----------------------------------------------------------------
    if shell.template:
        for i, c in enumerate(shell.template.chrome):
            h = c.h
            if c.h >= 0.8 * frame.page_h and height > frame.page_h:
                h = c.h + (height - frame.page_h)           # full-height panels grow with the page
            add(build_raw(f"{pid}-t{i:02d}", c.type, int(c.x), int(c.y), int(c.w), int(h), 0, 0,
                          c.objects, c.vco or None))
        add(_header(pid, page, frame.header, shell))
    else:
        add(build_shape(f"{pid}-canvas", 0, 0, frame.page_w, height, 0, 0, shell.canvas))
        nav = frame.nav or Rect(0, 0, 0, 0)
        add(build_shape(f"{pid}-nav", nav.x, 0, nav.w, height, 0, 0, shell.sidebar_color))
        b = frame.brand
        if b and shell.logo_item:
            add(build_image(f"{pid}-logo", shell.logo_item, b.x, b.y, b.w, b.h, 0, 0))
        elif b:
            add(build_textbox(f"{pid}-brand", [text_run(shell.brand, "20pt", bold=True, color="#000000")],
                              b.x, b.y, b.w, b.h, 0, 0, background="#FFFFFF", align="left"))
        add(_header(pid, page, frame.header, shell))

    # ---- content ----------------------------------------------------------------
    card_i = 0
    for i, v in enumerate(placed):
        style = None
        if shell.template:
            style = shell.template.style_for(VISUAL_TYPE.get(v.type, "tableEx"))
        add(build_visual(v, table, f"{pid}-v{i:02d}", 0, style=style))
        # a coloured accent bar over each KPI card (theme palette, cycled) — default shell only
        if v.type in ("card", "kpi") and not shell.template:
            colour = shell.data_colors[card_i % len(shell.data_colors)]
            card_i += 1
            add(build_shape(f"{pid}-a{i:02d}", v.x, v.y + 10, 6, max(8, v.h - 20), 0, 0, colour))
    for obj in body:
        add(obj)

    # "how to use this report" note, pinned to the bottom of the sidebar (default shell)
    n = frame.notes
    if n and shell.design.usage_notes and page.kind != "about":
        runs = [[text_run("How to use this report", "12pt", bold=True, color="#000000")]]
        for note in shell.design.usage_notes[:4]:
            runs.append([text_run(f"• {note}", "9pt", color="#000000")])
        add(build_textbox(f"{pid}-notes", runs, n.x, n.y + (height - frame.page_h), n.w, n.h, 0, 0,
                          background="#FFFFFF", align="left"))
    return out, height


def _header(pid: str, page: Page, r: Rect, shell: _Shell) -> dict:
    """Page title + its headline question (the question only if the header has room)."""
    ts = shell.template.title_style if shell.template else None
    unit = shell.frame.unit
    title_size = (ts.size if ts and ts.size else f"{int(24 * min(unit, 1.4))}pt")
    color = (ts.color if ts and ts.color else shell.ink)
    font = ts.font if ts else None
    paras = [[text_run(page.name, title_size, bold=(ts.bold if ts else True), color=color, font=font)]]
    if page.question and r.h >= 70 * unit:
        paras.append([text_run(page.question, f"{int(12 * min(unit, 1.4))}pt", color=_MUTED, font=font)])
    return build_textbox(f"{pid}-title", paras, r.x, r.y, r.w, r.h, 0, 0,
                         background=(ts.background if ts else None),
                         align=(ts.align if ts else "left"))


def _about_boxes(pid: str, page: Page, frame: Frame, shell: _Shell) -> list[dict]:
    """The About page: each section a white panel, laid out in two balanced columns."""
    c = frame.content
    gap = frame.gap
    col_w = (c.w - gap) // 2
    unit = frame.unit
    heights = []
    for _head, lines in page.sections:
        text_len = sum(max(1, len(ln) // 95 + 1) for ln in lines)
        heights.append(int((70 + 26 * text_len) * unit))
    cols = [c.y, c.y]
    out = []
    for i, ((head, lines), h) in enumerate(zip(page.sections, heights)):
        col = 0 if cols[0] <= cols[1] else 1
        x = c.x + col * (col_w + gap)
        y = cols[col]
        paras = [[text_run(head, f"{int(14 * min(unit, 1.4))}pt", bold=True, color=shell.ink)]]
        for ln in lines:
            paras.append([text_run(f"• {ln}", f"{int(10 * min(unit, 1.4))}pt", color=_MUTED)])
        out.append(build_textbox(f"{pid}-s{i:02d}", paras, x, y, col_w, h, 0, 0, background="#FFFFFF"))
        cols[col] = y + h + gap
    return out


def _unique(base: str, used: set[str]) -> str:
    name = base
    i = 1
    while name in used:
        name = f"{base}-{i}"
        i += 1
    used.add(name)
    return name
