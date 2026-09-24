"""Layout engine: place a page's visuals inside a :class:`Frame` on a 12-column editorial grid.

The design decides *what* each page shows; this module decides *where*. A frame describes the
page shell — where the header (title + headline question), filters, content, brand and notes
live. The default frame is pbigen's own sidebar shell; a template pack (from a customer's
``.pbix``) supplies a frame measured from their report, so generated visuals land inside
*their* design.

Inside the content region the grid reads like an editorial dashboard:

* a KPI band (cards, with room for the period-over-period subtitle),
* rows packed greedily by size hint (hero 8/12 + side 4/12, halves, thirds, full width),
  stretched to fill each row, with the hero row given more height,
* if a page has more rows than fit, the page grows taller instead of squashing charts.

Author: Arka Gupta
"""
from __future__ import annotations

from dataclasses import dataclass

from .design import SIZES, Page, Visual
from .schema import DATE, DATETIME, Schema

# default canvas + sidebar geometry (a large canvas so dense layouts are not clipped)
PAGE_W, PAGE_H = 1920, 1080
SIDEBAR_W = 300
LOGO_ZONE_H = 200
TITLE_H = 96
CARD_H = 150      # KPI cards carry value + label + delta subtitle
GAP = 22
MARGIN = 28
MIN_ROW_H = 300   # below this a chart stops being readable — grow the page instead


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


@dataclass
class Frame:
    """The page shell: canvas size and the regions each kind of element goes into."""

    page_w: int
    page_h: int
    content: Rect
    header: Rect
    filters: Rect | None = None
    nav: Rect | None = None          # drawn sidebar background (default shell only)
    brand: Rect | None = None        # logo / brand strip
    notes: Rect | None = None        # "how to use" box
    gap: int = GAP
    unit: float = 1.0                # scale vs the 1920-wide default (bigger canvases -> bigger cells)


def nav_x(nav_side: str) -> int:
    """Left edge of the navigation sidebar for the chosen side."""
    return 0 if nav_side == "left" else PAGE_W - SIDEBAR_W


def default_frame(nav_side: str = "left") -> Frame:
    nx = nav_x(nav_side)
    mx0 = (SIDEBAR_W + MARGIN) if nav_side == "left" else MARGIN
    mw = PAGE_W - SIDEBAR_W - 2 * MARGIN
    top = MARGIN + TITLE_H + GAP
    return Frame(
        page_w=PAGE_W, page_h=PAGE_H,
        header=Rect(mx0, MARGIN, mw, TITLE_H),
        content=Rect(mx0, top, mw, PAGE_H - top - MARGIN),
        nav=Rect(nx, 0, SIDEBAR_W, PAGE_H),
        brand=Rect(nx + 20, 28, SIDEBAR_W - 40, LOGO_ZONE_H - 60),
        filters=Rect(nx + 20, LOGO_ZONE_H, SIDEBAR_W - 40, PAGE_H - LOGO_ZONE_H - 340),
        notes=Rect(nx + 16, PAGE_H - 320, SIDEBAR_W - 32, 300),
    )


def _is_wide(v: Visual) -> bool:
    """A visual that shows many columns needs the full width."""
    if v.type == "matrix":
        return bool(v.series) or len(v.measures) >= 3
    if v.type == "table":
        return len(v.columns) + len(v.measures) >= 6
    return False


def _span(v: Visual) -> int:
    if v.size in SIZES:
        return SIZES[v.size]
    if _is_wide(v):
        return 12
    if v.type in ("donut", "pie", "treemap"):
        return 4
    return 6


def _place_slicers(page: Page, schema: Schema, frame: Frame, content: Rect) -> tuple[list[Visual], Rect]:
    """Slicers go in the frame's filter region (stacked if tall, a row if wide); without one they
    form a strip on top of the content area, which then shrinks."""
    real_dates = {c.name for c in schema.columns if c.dtype in (DATE, DATETIME)}
    out: list[Visual] = []
    u = frame.unit
    slicers = page.slicers[:7]
    if not slicers:
        return out, content
    region = frame.filters
    if region is None:
        h = int(76 * u)
        region = Rect(content.x, content.y, content.w, h)
        content = Rect(content.x, content.y + h + frame.gap, content.w, content.h - h - frame.gap)
    if region.h >= region.w:                       # a vertical rail: stack
        y = region.y
        for col in slicers:
            is_date = col in real_dates
            h = int((84 if is_date else 72) * u)
            if y + h > region.bottom:
                break
            out.append(Visual("slicer", title=col, category=col,
                              slicer_mode="Between" if is_date else "Dropdown",
                              x=region.x, y=y, w=region.w, h=h))
            y += h + int(12 * u)
    else:                                          # a horizontal band: side by side
        n = len(slicers)
        g = int(12 * u)
        w = (region.w - (n - 1) * g) // n
        for i, col in enumerate(slicers):
            is_date = col in real_dates
            out.append(Visual("slicer", title=col, category=col,
                              slicer_mode="Between" if is_date else "Dropdown",
                              x=region.x + i * (w + g), y=region.y, w=w, h=region.h))
    return out, content


def pack(page: Page, schema: Schema, nav_side: str = "left", frame: Frame | None = None) -> list[Visual]:
    """Return the page's visuals with x/y/w/h assigned, plus positioned slicer visuals."""
    frame = frame or default_frame(nav_side)
    gap = frame.gap
    placed, content = _place_slicers(page, schema, frame, frame.content)
    x0, y, cw = content.x, content.y, content.w

    cards = [v for v in page.visuals if v.type in ("card", "kpi")][:8]
    body = [v for v in page.visuals if v.type not in ("card", "kpi", "slicer")]

    card_h = int(CARD_H * frame.unit)
    if cards:
        per = len(cards) if len(cards) <= 6 else 4
        for i0 in range(0, len(cards), per):
            row = cards[i0:i0 + per]
            n = len(row)
            w = (cw - (n - 1) * gap) // n
            for i, v in enumerate(row):
                v.x, v.y, v.w, v.h = x0 + i * (w + gap), y, w, card_h
                placed.append(v)
            y += card_h + gap

    # greedy rows on the 12-column grid
    rows: list[list[Visual]] = []
    cur: list[Visual] = []
    used = 0
    for v in body:
        s = _span(v)
        if cur and used + s > 12:
            rows.append(cur)
            cur, used = [], 0
        cur.append(v)
        used += s
    if cur:
        rows.append(cur)
    if not rows:
        return placed

    weights = [1.35 if any(v.size == "hero" for v in r) else 1.0 for r in rows]
    avail = content.bottom - y - (len(rows) - 1) * gap
    unit_h = avail / sum(weights)
    min_h = int(MIN_ROW_H * frame.unit)
    for r, wt in zip(rows, weights):
        row_h = max(min_h, int(unit_h * wt))
        spans = [_span(v) for v in r]
        total = sum(spans)
        inner = cw - (len(r) - 1) * gap
        x = x0
        for i, (v, s) in enumerate(zip(r, spans)):
            w = (x0 + cw - x) if i == len(r) - 1 else int(inner * s / total)
            v.x, v.y, v.w, v.h = x, y, w, row_h
            placed.append(v)
            x += w + gap
        y += row_h + gap
    return placed


def page_height(placed: list[Visual], frame: Frame) -> int:
    """The canvas height a page needs (grows past the frame when rows would be too short)."""
    bottom = max([v.y + v.h for v in placed] or [0])
    return max(frame.page_h, bottom + MARGIN)
