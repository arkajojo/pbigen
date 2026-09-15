"""Layout-packer tests: sidebar filters, KPI row, geometry within the canvas.

Author: Arka Gupta
"""
from __future__ import annotations

from pbigen.core.design import Page, Visual
from pbigen.core.layout import PAGE_H, PAGE_W, SIDEBAR_W, pack
from pbigen.core.schema import Column, Schema


def _schema():
    return Schema("t", [Column("d", "datetime"), Column("region", "string", cardinality=4),
                        Column("revenue", "float")])


def test_slicers_land_in_sidebar_with_date_as_range():
    page = Page("P", visuals=[Visual("card", "Revenue", measures=["Revenue"])],
                slicers=["d", "region"])
    placed = pack(page, _schema())
    slicers = [v for v in placed if v.type == "slicer"]
    assert {s.category for s in slicers} == {"d", "region"}
    assert all(s.x + s.w <= SIDEBAR_W for s in slicers)          # inside the sidebar
    assert next(s for s in slicers if s.category == "d").slicer_mode == "Between"
    assert next(s for s in slicers if s.category == "region").slicer_mode == "Dropdown"


def test_everything_fits_the_canvas():
    page = Page("P", visuals=[
        Visual("card", "A", measures=["A"]), Visual("card", "B", measures=["B"]),
        Visual("line", "Trend", measures=["A"], category="d"),
        Visual("bar", "By region", measures=["A"], category="region"),
        Visual("table", "Detail", measures=["A"], columns=["d", "region"]),
    ], slicers=["region"])
    placed = pack(page, _schema())
    for v in placed:
        assert v.w > 0 and v.h > 0
        assert 0 <= v.x and v.x + v.w <= PAGE_W + 1
        assert 0 <= v.y and v.y + v.h <= PAGE_H + 1
