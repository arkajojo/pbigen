"""Themes — bring your own, or use a built-in.

``get_theme(spec)`` accepts:

* ``None`` or a built-in name (``"midnight"``, ``"slate"``, ``"aurora"``) -> a bundled theme dict.
* a path to a Power BI theme ``.json`` -> loaded and used as-is (your corporate theme drops in).

A theme returns a standard Power BI theme document (``name``, ``dataColors``, ``visualStyles`` …)
plus two convenience keys the emitter reads for the navigation sidebar: ``sidebarColor`` and
``accentColor``. Those are stripped before the theme is written, so the file stays valid.

Author: Arka Gupta
"""
from __future__ import annotations

import copy
import json
import os

_BUILTIN_DIR = os.path.dirname(__file__)
_BUILTINS = {"midnight": "midnight.json", "slate": "slate.json", "aurora": "aurora.json"}
_DEFAULT = "midnight"


def available_themes() -> list[str]:
    return sorted(_BUILTINS)


def _load_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def get_theme(spec: str | None = None) -> dict:
    if spec and os.path.exists(spec):
        theme = _load_file(spec)
        theme.setdefault("sidebarColor", "#1B1F3B")
        theme.setdefault("accentColor", "#FFFFFF")
        return theme
    key = (spec or _DEFAULT).lower()
    if key not in _BUILTINS:
        raise ValueError(f"unknown theme {spec!r}; use a file path or one of {available_themes()}")
    return _load_file(os.path.join(_BUILTIN_DIR, _BUILTINS[key]))


def split_chrome(theme: dict) -> tuple[dict, str, str]:
    """Return (clean theme document, sidebar color, accent color)."""
    theme = copy.deepcopy(theme)
    sidebar = theme.pop("sidebarColor", "#1B1F3B")
    accent = theme.pop("accentColor", "#FFFFFF")
    return theme, sidebar, accent


__all__ = ["get_theme", "available_themes", "split_chrome"]
