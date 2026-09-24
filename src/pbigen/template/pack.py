"""Build, save and load template packs (see the package docstring).

The builder picks the report's richest page as the reference, then measures:

* **content** — the bounding box of its data visuals (where their charts live),
* **filters** — the bounding box of its slicers,
* **header** — the most prominent textbox outside the content (their title), with its font,
* **chrome** — shapes / images / page navigators outside the content (sidebars, header bands,
  logos) plus large backdrop panels behind it; per-visual decorations and page-specific text
  are left out,
* **styles** — per visual type, the formatting of their most-styled visual of that type, with
  every data-bound property (field selectors, conditional formats, titles text) removed.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field

from ..core.layout import Frame, Rect
from .reader import IMAGE_EXT, RawPage, RawVisual, read_report

PACK_VERSION = 1
_CHROME_TYPES = {"shape", "basicShape", "image", "pageNavigator", "bookmarkNavigator"}
_DATA_BOUND_KEYS = {"Measure", "Column", "Aggregation", "HierarchyLevel", "Conditional",
                    "FillRule", "SourceRef", "Subquery"}
# properties that carry the template's *content* rather than its look
_CONTENT_PROPS = {"text", "startDate", "endDate", "paragraphs", "value", "words", "imageUrl",
                  "selfFilter", "filter", "isInvertedSelectionMode", "mode"}
_STYLE_DROP_OBJECTS = {"data", "stopWords", "selection", "general_filter"}


@dataclass
class TitleStyle:
    font: str | None = None
    size: str | None = None          # e.g. "28pt"
    color: str | None = None
    bold: bool = True
    align: str = "left"
    background: str | None = None


@dataclass
class ChromeItem:
    type: str
    x: float
    y: float
    w: float
    h: float
    z: float
    objects: dict = field(default_factory=dict)
    vco: dict = field(default_factory=dict)


@dataclass
class TemplatePack:
    """A report's reusable look: canvas, frame, chrome, title style, per-type styles, theme."""

    name: str
    source: str
    page_w: int
    page_h: int
    content: Rect
    header: Rect
    filters: Rect | None = None
    page_objects: dict = field(default_factory=dict)
    chrome: list[ChromeItem] = field(default_factory=list)
    title_style: TitleStyle = field(default_factory=TitleStyle)
    styles: dict[str, dict] = field(default_factory=dict)
    theme_file: str | None = None
    assets: list[str] = field(default_factory=list)
    root: str = ""                   # folder the pack lives in (set on load)
    reference_page: str = ""
    version: int = PACK_VERSION

    # -- use ------------------------------------------------------------------
    def frame(self) -> Frame:
        unit = max(0.6, min(1.8, self.content.w / 1592))
        return Frame(page_w=self.page_w, page_h=self.page_h, content=self.content, header=self.header,
                     filters=self.filters, gap=max(12, int(22 * unit)), unit=unit)

    def theme(self) -> dict | None:
        if not self.theme_file:
            return None
        p = os.path.join(self.root, self.theme_file)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8-sig") as fh:
            return json.load(fh)

    def asset_path(self, name: str) -> str:
        return os.path.join(self.root, "assets", name)

    def style_for(self, visual_type: str) -> dict | None:
        return self.styles.get(visual_type) or self.styles.get("*")

    # -- persistence ----------------------------------------------------------
    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("root", None)
        return d

    def save(self, out_dir: str) -> str:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "pack.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_json(), fh, indent=2)
        self.root = out_dir
        return path


def load_pack(path: str) -> TemplatePack:
    """Load a pack from its folder (or its ``pack.json``)."""
    root = path if os.path.isdir(path) else os.path.dirname(path)
    with open(os.path.join(root, "pack.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    rect = lambda r: Rect(**r) if r else None  # noqa: E731
    return TemplatePack(
        name=d["name"], source=d.get("source", ""), page_w=int(d["page_w"]), page_h=int(d["page_h"]),
        content=rect(d["content"]), header=rect(d["header"]), filters=rect(d.get("filters")),
        page_objects=d.get("page_objects") or {},
        chrome=[ChromeItem(**c) for c in d.get("chrome", [])],
        title_style=TitleStyle(**(d.get("title_style") or {})),
        styles=d.get("styles") or {}, theme_file=d.get("theme_file"), assets=d.get("assets") or [],
        root=root, reference_page=d.get("reference_page", ""), version=d.get("version", PACK_VERSION),
    )


def resolve_template(spec: str, work_dir: str | None = None) -> TemplatePack:
    """A pack folder / pack.json, or a report file (.pbix/.pbit/.pbip/.Report) compiled on the fly."""
    if os.path.isdir(spec) and os.path.exists(os.path.join(spec, "pack.json")):
        return load_pack(spec)
    if spec.endswith("pack.json"):
        return load_pack(spec)
    out = work_dir or tempfile.mkdtemp(prefix="pbigen-template-")
    return build_pack(spec, out)


# --------------------------------------------------------------------------- building
def _walk_has_data_binding(node) -> bool:
    if isinstance(node, dict):
        if any(k in _DATA_BOUND_KEYS for k in node):
            return True
        return any(_walk_has_data_binding(v) for v in node.values())
    if isinstance(node, list):
        return any(_walk_has_data_binding(v) for v in node)
    return False


def sanitize_objects(objects: dict, drop_objects: set[str] | frozenset = frozenset()) -> dict:
    """Keep only look-and-feel: no field selectors, no data-bound expressions, no content text."""
    out: dict = {}
    for key, entries in (objects or {}).items():
        if key in drop_objects or not isinstance(entries, list):
            continue
        kept = []
        for e in entries:
            if not isinstance(e, dict) or e.get("selector"):
                continue                                  # per-data-point / per-field formatting
            props = {k: v for k, v in (e.get("properties") or {}).items()
                     if k not in _CONTENT_PROPS and not _walk_has_data_binding(v)}
            if props:
                kept.append({"properties": props})
        if kept:
            out[key] = kept[:1]
    return out


def _bbox(items: list[RawVisual]) -> Rect | None:
    if not items:
        return None
    x0 = min(v.x for v in items)
    y0 = min(v.y for v in items)
    x1 = max(v.x + v.w for v in items)
    y1 = max(v.y + v.h for v in items)
    return Rect(int(x0), int(y0), int(x1 - x0), int(y1 - y0))


def _inside(v: RawVisual, r: Rect, tol: float = 4) -> bool:
    cx, cy = v.x + v.w / 2, v.y + v.h / 2
    return r.x - tol <= cx <= r.x + r.w + tol and r.y - tol <= cy <= r.y + r.h + tol


def _overlap_ratio(v: RawVisual, r: Rect) -> float:
    ix = max(0.0, min(v.x + v.w, r.x + r.w) - max(v.x, r.x))
    iy = max(0.0, min(v.y + v.h, r.y + r.h) - max(v.y, r.y))
    area = max(1.0, v.w * v.h)
    return (ix * iy) / area


def _text_runs(v: RawVisual) -> list[dict]:
    runs = []
    for g in v.objects.get("general", []):
        for p in (g.get("properties") or {}).get("paragraphs", []) or []:
            runs.extend(p.get("textRuns", []) or [])
    return runs


def _font_pt(run: dict) -> float:
    size = str((run.get("textStyle") or {}).get("fontSize", "") or "")
    m = re.match(r"([\d.]+)", size)
    return float(m.group(1)) if m else 11.0


def _literal(expr) -> str | None:
    try:
        return expr["solid"]["color"]["expr"]["Literal"]["Value"].strip("'")
    except (KeyError, TypeError, AttributeError):
        return None


def _data_visuals(p: RawPage) -> list[RawVisual]:
    return [v for v in p.visuals if v.is_data and v.type != "slicer" and v.type not in _CHROME_TYPES]


def _pick_page(pages: list[RawPage], name: str | None) -> RawPage:
    if name:
        for p in pages:
            if p.name.lower() == name.lower():
                return p
        raise ValueError(f"page {name!r} not found; pages: {[p.name for p in pages]}")
    return max(pages, key=lambda p: (len(_data_visuals(p)), len(p.visuals)))


def _collect_styles(pages: list[RawPage]) -> dict[str, dict]:
    """Per visual type: the most-formatted example across all pages, sanitized. Plus a ``*``
    default from the most common container formatting."""
    best: dict[str, tuple[int, dict]] = {}
    vco_counter: Counter = Counter()
    vco_by_key: dict[str, dict] = {}
    for p in pages:
        for v in p.visuals:
            if not v.is_data and v.type != "slicer":
                continue
            drop = _STYLE_DROP_OBJECTS | ({"general", "header"} if v.type == "slicer" else set())
            objs = sanitize_objects(v.objects, drop)
            vco = sanitize_objects(v.vco)
            score = sum(len(e[0]["properties"]) for e in objs.values()) + \
                sum(len(e[0]["properties"]) for e in vco.values())
            if score and score > best.get(v.type, (-1, {}))[0]:
                best[v.type] = (score, {"objects": objs, "visualContainerObjects": vco})
            if vco and v.type != "slicer":
                key = json.dumps(vco, sort_keys=True)
                vco_counter[key] += 1
                vco_by_key[key] = vco
    styles = {t: s for t, (_, s) in best.items()}
    if vco_counter:
        styles["*"] = {"objects": {}, "visualContainerObjects": vco_by_key[vco_counter.most_common(1)[0][0]]}
    # our emitter uses clustered charts; borrow the stacked look if that is all they had
    alias = {"clusteredColumnChart": "columnChart", "clusteredBarChart": "barChart",
             "columnChart": "clusteredColumnChart", "barChart": "clusteredBarChart",
             "areaChart": "lineChart", "lineClusteredColumnComboChart": "clusteredColumnChart",
             "waterfallChart": "clusteredColumnChart", "pieChart": "donutChart", "donutChart": "pieChart",
             "pivotTable": "tableEx", "tableEx": "pivotTable"}
    for ours, theirs in alias.items():
        if ours not in styles and theirs in styles:
            styles[ours] = styles[theirs]
    return styles


def build_pack(report_path: str, out_dir: str, page: str | None = None,
               name: str | None = None) -> TemplatePack:
    """Compile ``report_path`` (.pbix/.pbit/.pbip/.Report) into a template pack at ``out_dir``."""
    rep = read_report(report_path)
    if not rep.pages:
        raise ValueError(f"{report_path}: the report has no pages")
    ref = _pick_page(rep.pages, page)
    pw, ph = int(ref.width), int(ref.height)
    unit = pw / 1920

    data = _data_visuals(ref)
    slicers = [v for v in ref.visuals if v.type == "slicer"]
    margin = int(28 * unit) or 16
    content = _bbox(data) or Rect(margin, int(140 * unit), pw - 2 * margin, ph - int(140 * unit) - margin)
    filters = _bbox(slicers)
    if filters and content:
        # slicers inside the content box: carve them out (a filter band above/beside the charts)
        inter = _overlap_ratio(RawVisual("", filters.x, filters.y, filters.w, filters.h), content)
        if inter > 0.5:
            if filters.w >= filters.h:
                new_top = filters.y + filters.h + margin // 2
                content = Rect(content.x, new_top, content.w, content.y + content.h - new_top)
            else:
                filters = None

    # title: the most prominent textbox outside the content area
    title_box: RawVisual | None = None
    title_run: dict = {}
    best_pt = 0.0
    top_zone = content.y + 0.15 * content.h
    for v in ref.visuals:
        if v.type != "textbox" or _inside(v, content) or (v.y + v.h / 2) > top_zone:
            continue                                     # titles sit above/at the top, not in footers
        runs = _text_runs(v)
        pt = max((_font_pt(r) for r in runs), default=0)
        if runs and pt > best_pt:
            best_pt, title_box, title_run = pt, v, max(runs, key=_font_pt)
    if title_box:
        header = Rect(int(title_box.x), int(title_box.y), int(title_box.w), int(max(title_box.h, 60 * unit)))
        ts = title_run.get("textStyle") or {}
        align = "left"
        for g in title_box.objects.get("general", []):
            for p in (g.get("properties") or {}).get("paragraphs", []) or []:
                align = p.get("horizontalTextAlignment", align)
        bg = None
        for b in title_box.vco.get("background", []):
            bg = _literal((b.get("properties") or {}).get("color"))
        title_style = TitleStyle(font=ts.get("fontFamily"), size=ts.get("fontSize"), color=ts.get("color"),
                                 bold=str(ts.get("fontWeight", "")).lower() == "bold", align=align, background=bg)
    else:
        hh = int(96 * unit)
        if content.y >= hh + margin:
            header = Rect(content.x, content.y - hh - margin // 2, content.w, hh)
        else:
            header = Rect(content.x, content.y, content.w, hh)
            content = Rect(content.x, content.y + hh + margin // 2, content.w, content.h - hh - margin // 2)
        title_style = TitleStyle()
    if header.y < content.y < header.y + header.h:          # never let the title overlap charts
        top = header.y + header.h + margin // 2
        content = Rect(content.x, top, content.w, content.y + content.h - top)

    # chrome: shapes/images/navigators outside the content (or big backdrops behind it)
    carea = max(1, content.w * content.h)
    chrome: list[ChromeItem] = []
    for v in ref.visuals:
        if v.type not in _CHROME_TYPES or v.is_data:
            continue
        backdrop = v.type in ("shape", "basicShape") and (v.w * v.h) >= 0.4 * carea
        if _inside(v, content) and not backdrop:
            continue                                     # a decoration of one of their visuals
        if title_box is not None and v is title_box:
            continue
        objs = sanitize_objects(v.objects) if v.type != "image" else _keep_image(v.objects)
        chrome.append(ChromeItem(v.type, v.x, v.y, v.w, v.h, v.z, objs, sanitize_objects(v.vco)))
    chrome.sort(key=lambda c: c.z)

    # theme + assets
    os.makedirs(os.path.join(out_dir, "assets"), exist_ok=True)
    theme_file = None
    assets: list[str] = []
    for fname, blob in rep.resources.items():
        ext = os.path.splitext(fname)[1].lower()
        if ext == ".json":
            try:
                obj = json.loads(blob.decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(obj, dict) and ("dataColors" in obj or "visualStyles" in obj):
                if theme_file is None or fname == rep.custom_theme_name:
                    theme_file = "theme.json"
                    with open(os.path.join(out_dir, theme_file), "w", encoding="utf-8") as fh:
                        json.dump(obj, fh, indent=2)
        elif ext in IMAGE_EXT:
            with open(os.path.join(out_dir, "assets", fname), "wb") as fh:
                fh.write(blob)
            assets.append(fname)

    page_objects = {k: v for k, v in (ref.objects or {}).items()
                    if k in ("background", "outspace", "outspacePane", "displayArea")}

    pack = TemplatePack(
        name=name or os.path.splitext(os.path.basename(report_path.rstrip("/")))[0],
        source=os.path.basename(report_path.rstrip("/")),
        page_w=pw, page_h=ph, content=content, header=header, filters=filters,
        page_objects=page_objects, chrome=chrome, title_style=title_style,
        styles=_collect_styles(rep.pages), theme_file=theme_file, assets=sorted(assets),
        reference_page=ref.name,
    )
    pack.save(out_dir)
    return pack


def _keep_image(objects: dict) -> dict:
    """Images keep their resource binding (that *is* the look) plus scaling."""
    out = {}
    for key in ("general", "imageScaling"):
        if key in objects:
            out[key] = objects[key][:1]
    return out


def referenced_images(pack: TemplatePack) -> set[str]:
    """Asset names the pack's page background and chrome actually use."""
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            item = node.get("ResourcePackageItem")
            if isinstance(item, dict) and item.get("ItemName"):
                found.add(item["ItemName"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(pack.page_objects)
    for c in pack.chrome:
        walk(c.objects)
        walk(c.vco)
    return found & set(pack.assets)


def describe(pack: TemplatePack) -> str:
    """A human summary of what the pack captured (used by ``pbigen template show``)."""
    lines = [
        f"Template pack: {pack.name}  (from {pack.source}, reference page '{pack.reference_page}')",
        f"  canvas      {pack.page_w} x {pack.page_h}",
        f"  content     x={pack.content.x} y={pack.content.y} w={pack.content.w} h={pack.content.h}",
        f"  header      x={pack.header.x} y={pack.header.y} w={pack.header.w} h={pack.header.h}"
        + (f"  font={pack.title_style.font or 'theme'} {pack.title_style.size or ''}" if pack.title_style else ""),
        "  filters     " + (f"x={pack.filters.x} y={pack.filters.y} w={pack.filters.w} h={pack.filters.h}"
                           if pack.filters else "none (slicers become a band above the content)"),
        f"  chrome      {len(pack.chrome)} element(s): "
        + ", ".join(sorted(Counter(c.type for c in pack.chrome).elements())) if pack.chrome else "  chrome      none",
        f"  background  {'yes' if pack.page_objects.get('background') or pack.page_objects.get('outspace') else 'none'}",
        f"  styles      {', '.join(sorted(k for k in pack.styles if k != '*')) or 'none'}",
        f"  theme       {pack.theme_file or 'none (uses the report base theme)'}",
        f"  assets      {len(pack.assets)} image(s)",
    ]
    return "\n".join(lines)
