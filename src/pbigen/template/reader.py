"""Read a Power BI report's layout into one normalised structure.

Power BI stores a report's layout in two formats:

* **legacy** — ``Report/Layout`` inside a ``.pbix``/``.pbit`` (UTF-16 JSON; each visual's config
  is a JSON *string*; container formatting lives in ``vcObjects``),
* **PBIR** — a ``definition/`` folder of ``page.json`` + ``visuals/*/visual.json`` files (in a
  PBIP ``.Report`` folder, or inside a ``.pbix`` saved with the PBIR preview on).

Both become :class:`RawReport` here, so the pack builder never cares which one it got.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, field

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}


@dataclass
class RawVisual:
    type: str
    x: float
    y: float
    w: float
    h: float
    z: float = 0.0
    objects: dict = field(default_factory=dict)
    vco: dict = field(default_factory=dict)
    is_data: bool = False        # bound to fields (has a query / projections)


@dataclass
class RawPage:
    name: str
    width: float
    height: float
    objects: dict = field(default_factory=dict)
    visuals: list[RawVisual] = field(default_factory=list)


@dataclass
class RawReport:
    pages: list[RawPage] = field(default_factory=list)
    report_objects: dict = field(default_factory=dict)
    custom_theme_name: str | None = None
    #: registered resources: file name -> bytes (themes, images)
    resources: dict[str, bytes] = field(default_factory=dict)


def _decode_layout(raw: bytes) -> dict:
    for enc in ("utf-16-le", "utf-16", "utf-8-sig"):
        try:
            text = raw.decode(enc)
            return json.loads(text.lstrip("﻿"))
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError("could not decode Report/Layout")


def _legacy(layout: dict) -> tuple[list[RawPage], dict, str | None]:
    cfg = json.loads(layout.get("config") or "{}")
    theme = ((cfg.get("themeCollection") or {}).get("customTheme") or {}).get("name")
    pages: list[RawPage] = []
    for s in sorted(layout.get("sections", []), key=lambda s: s.get("ordinal", 0)):
        scfg = json.loads(s.get("config") or "{}")
        page = RawPage(s.get("displayName") or s.get("name") or "Page",
                       float(s.get("width", 1280)), float(s.get("height", 720)),
                       scfg.get("objects") or {})
        for vc in s.get("visualContainers", []):
            try:
                c = json.loads(vc.get("config") or "{}")
            except ValueError:
                continue
            sv = c.get("singleVisual")
            if not sv:
                continue                                   # groups: children carry absolute positions
            page.visuals.append(RawVisual(
                sv.get("visualType", ""), float(vc.get("x", 0)), float(vc.get("y", 0)),
                float(vc.get("width", 0)), float(vc.get("height", 0)), float(vc.get("z", 0)),
                sv.get("objects") or {}, sv.get("vcObjects") or {},
                bool(sv.get("projections") or sv.get("prototypeQuery")),
            ))
        pages.append(page)
    return pages, cfg.get("objects") or {}, theme


def _pbir_from_files(read, listdir_pages) -> tuple[list[RawPage], dict, str | None]:
    """PBIR: ``read(path) -> bytes|None`` relative to ``definition/``; ``listdir_pages()`` yields
    (page_dir, [visual.json paths])."""
    report = json.loads(read("report.json") or b"{}")
    theme = ((report.get("themeCollection") or {}).get("customTheme") or {}).get("name")
    order = []
    meta = read("pages/pages.json")
    if meta:
        order = json.loads(meta).get("pageOrder", [])
    pages: dict[str, RawPage] = {}
    for pdir, vpaths in listdir_pages():
        pj = read(f"{pdir}/page.json")
        if not pj:
            continue
        p = json.loads(pj)
        page = RawPage(p.get("displayName") or p.get("name", "Page"),
                       float(p.get("width", 1280)), float(p.get("height", 720)), p.get("objects") or {})
        for vp in vpaths:
            try:
                vj = json.loads(read(vp) or b"{}")
            except ValueError:
                continue
            vis = vj.get("visual")
            if not vis:
                continue
            pos = vj.get("position", {})
            page.visuals.append(RawVisual(
                vis.get("visualType", ""), float(pos.get("x", 0)), float(pos.get("y", 0)),
                float(pos.get("width", 0)), float(pos.get("height", 0)), float(pos.get("z", 0)),
                vis.get("objects") or {}, vis.get("visualContainerObjects") or {},
                bool(vis.get("query")),
            ))
        pages[os.path.basename(pdir)] = page
    ordered = [pages[k] for k in order if k in pages] + [v for k, v in pages.items() if k not in order]
    return ordered, report.get("objects") or {}, theme


def read_report(path: str) -> RawReport:
    """Read a ``.pbix`` / ``.pbit`` (legacy or PBIR inside), or a PBIP ``.Report`` folder / ``.pbip``."""
    if os.path.isdir(path) or path.lower().endswith(".pbip"):
        return _read_folder(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    rep = RawReport()
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "Report/Layout" in names:
            rep.pages, rep.report_objects, rep.custom_theme_name = _legacy(_decode_layout(z.read("Report/Layout")))
        else:
            base = next((n[: n.index("definition/") + len("definition/")] for n in names
                         if "definition/report.json" in n), None)
            if base is None:
                raise ValueError(f"{path}: no report layout found (not a Power BI report file?)")

            def read(rel: str) -> bytes | None:
                return z.read(base + rel) if base + rel in names else None

            def listdir_pages():
                pdirs = sorted({n[len(base):].rsplit("/", 1)[0] for n in names
                                if n.startswith(base + "pages/") and n.endswith("/page.json")})
                for pd in pdirs:
                    yield pd, [n[len(base):] for n in names
                               if n.startswith(base + pd + "/visuals/") and n.endswith("/visual.json")]

            rep.pages, rep.report_objects, rep.custom_theme_name = _pbir_from_files(read, listdir_pages)
        for n in names:
            low = n.lower()
            if "registeredresources/" in low and not low.endswith("/"):
                rep.resources[os.path.basename(n)] = z.read(n)
    return rep


def _read_folder(path: str) -> RawReport:
    root = path
    if path.lower().endswith(".pbip"):
        d = os.path.dirname(os.path.abspath(path))
        stem = os.path.splitext(os.path.basename(path))[0]
        root = os.path.join(d, f"{stem}.Report")
    if not root.rstrip("/").endswith(".Report"):
        cands = [os.path.join(root, n) for n in os.listdir(root) if n.endswith(".Report")]
        if not cands:
            raise ValueError(f"{path}: no .Report folder found")
        root = cands[0]
    defn = os.path.join(root, "definition")

    def read(rel: str) -> bytes | None:
        p = os.path.join(defn, rel)
        return open(p, "rb").read() if os.path.exists(p) else None

    def listdir_pages():
        pages_dir = os.path.join(defn, "pages")
        if not os.path.isdir(pages_dir):
            return
        for pd in sorted(os.listdir(pages_dir)):
            vdir = os.path.join(pages_dir, pd, "visuals")
            vps = []
            if os.path.isdir(vdir):
                vps = [f"pages/{pd}/visuals/{v}/visual.json" for v in sorted(os.listdir(vdir))
                       if os.path.exists(os.path.join(vdir, v, "visual.json"))]
            yield f"pages/{pd}", vps

    rep = RawReport()
    rep.pages, rep.report_objects, rep.custom_theme_name = _pbir_from_files(read, listdir_pages)
    res = os.path.join(root, "StaticResources", "RegisteredResources")
    if os.path.isdir(res):
        for n in os.listdir(res):
            with open(os.path.join(res, n), "rb") as fh:
                rep.resources[n] = fh.read()
    return rep
