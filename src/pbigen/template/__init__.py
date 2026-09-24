"""Template packs: turn a customer's own Power BI report into a reusable design shell.

    pbigen template build their_report.pbix --out my_pack      # once (or pass the .pbix directly)
    pbigen generate --source ... --template my_pack             # every new dashboard

A *template pack* is a small folder that captures everything about a report's **look** and
nothing about its data:

* ``theme.json`` — the report's custom theme (colours, fonts, visual-style defaults),
* ``assets/`` — its images: page backgrounds, logos, icons,
* ``pack.json`` — the page canvas (size, background/wallpaper), the **frame** measured from the
  report (where the header, filters and content live), the **chrome** (sidebar panels, logo,
  page navigator …) with exact positions, the **title style**, and per-visual-type **formatting**
  (borders, radius, shadows, title fonts, slicer styling …) with every data binding stripped.

``pbigen generate --template`` then renders a brand-new, data-driven dashboard *inside* that
shell: your pages, your measures, their design. Reads legacy ``.pbix``/``.pbit`` layouts and
PBIR (``.Report`` folders or PBIR-format ``.pbix``).

Author: Arka Gupta
"""
from __future__ import annotations

from .pack import TemplatePack, build_pack, load_pack, resolve_template

__all__ = ["TemplatePack", "build_pack", "load_pack", "resolve_template"]
