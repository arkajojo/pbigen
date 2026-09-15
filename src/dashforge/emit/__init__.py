"""Emitters — turn a design into on-disk BI artifacts.

Today: Power BI (PBIP/PBIR report + TMDL semantic model). The seam is deliberately narrow
(``write_project``) so other targets can be added without touching the design brain.

Author: Arka Gupta
"""
from __future__ import annotations

from .pbir import write_project

__all__ = ["write_project"]
