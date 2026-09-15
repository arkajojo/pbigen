"""Layout packer: place a page's visuals on a wide canvas with a left filter sidebar.

The design brain decides *what* each page shows; this module decides *where*, reliably:
a left sidebar for the logo + stacked filters + a "how to use" note, and a main area with a
KPI card row and charts/tables packed by footprint (wide pivots full-width, narrow ones paired).

Author: Arka Gupta
"""
from __future__ import annotations

from .design import Page, Visual
from .schema import DATETIME, Schema

# canvas + sidebar geometry (a large canvas so dense layouts are not clipped)
PAGE_W, PAGE_H = 1920, 1080
SIDEBAR_W = 300
LOGO_ZONE_H = 200
TITLE_H = 84
CARD_H = 140      # taller KPI cards read as executive panels
GAP = 22          # more breathing room between visuals
MARGIN = 28       # a touch more page padding


def _is_wide(v: Visual) -> bool:
    """A visual that shows many columns needs the full width."""
    if v.type == "matrix":
        return bool(v.series) or len(v.measures) >= 3
    if v.type == "table":
        return len(v.columns) + len(v.measures) >= 6
    return False


def nav_x(nav_side: str) -> int:
    """Left edge of the navigation sidebar for the chosen side."""
    return 0 if nav_side == "left" else PAGE_W - SIDEBAR_W


def pack(page: Page, schema: Schema, nav_side: str = "left") -> list[Visual]:
    """Return the page's visuals with x/y/w/h assigned, plus positioned slicer visuals."""
    real_dates = {c.name for c in schema.columns if c.dtype == DATETIME}
    placed: list[Visual] = []

    nx = nav_x(nav_side)
    mx0 = (SIDEBAR_W + MARGIN) if nav_side == "left" else MARGIN   # main content left edge
    mw = PAGE_W - SIDEBAR_W - 2 * MARGIN
    bottom = PAGE_H - MARGIN

    # slicers stacked in the sidebar; real dates render as a range slider
    sy = LOGO_ZONE_H
    for col in page.slicers[:7]:
        is_date = col in real_dates
        h = 84 if is_date else 72
        placed.append(Visual("slicer", title=col, category=col,
                             slicer_mode="Between" if is_date else "Dropdown",
                             x=nx + 20, y=sy, w=SIDEBAR_W - 40, h=h))
        sy += h + 12

    cards = [v for v in page.visuals if v.type in ("card", "kpi")][:8]
    body = [v for v in page.visuals if v.type not in ("card", "kpi")]

    y = MARGIN + TITLE_H + GAP     # equal gap below the page title, same as between all rows
    if cards:
        per = 4 if len(cards) > 3 else len(cards)
        for i0 in range(0, len(cards), per):
            row = cards[i0:i0 + per]
            n = len(row)
            w = (mw - (n - 1) * GAP) // n
            for i, v in enumerate(row):
                v.x, v.y, v.w, v.h = mx0 + i * (w + GAP), y, w, CARD_H
                placed.append(v)
            y += CARD_H + GAP

    wide = [v for v in body if _is_wide(v)]
    charts = [v for v in body if not _is_wide(v) and v.type not in ("table", "matrix")]
    ntables = [v for v in body if not _is_wide(v) and v.type in ("table", "matrix")]
    pairable: list[Visual] = []                # interleave so a narrow table pairs with a chart
    while charts or ntables:
        if charts:
            pairable.append(charts.pop(0))
        if ntables:
            pairable.append(ntables.pop(0))
    rows = [[wv] for wv in wide] + [pairable[i:i + 2] for i in range(0, len(pairable), 2)]

    n = max(1, len(rows))
    row_h = (bottom - y - (n - 1) * GAP) // n
    for r in rows:
        x = mx0
        widths = [mw] if len(r) == 1 else [(mw - GAP) // 2] * 2
        for w, v in zip(widths, r):
            v.x, v.y, v.w, v.h = x, y, w, row_h
            placed.append(v)
            x += w + GAP
        y += row_h + GAP
    return placed
