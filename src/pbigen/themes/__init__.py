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
    # utf-8-sig tolerates a byte-order mark, which gallery / Windows-exported theme JSONs often carry.
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _is_dark(color: str | None) -> bool:
    """True if a #hex colour is dark enough for white nav text to read on it."""
    if not isinstance(color, str) or not color.startswith("#"):
        return False
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return False
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return False
    return (0.299 * r + 0.587 * g + 0.114 * b) < 130


def get_theme(spec: str | None = None) -> dict:
    if spec and os.path.exists(spec):
        theme = _load_file(spec)
        # a bring-your-own / extracted theme rarely defines a sidebar colour — derive one from the
        # theme's own dark brand colour so the nav is cohesive instead of a fixed default.
        fg = theme.get("foreground") or theme.get("maximum")
        theme.setdefault("sidebarColor", fg if _is_dark(fg) else "#1B1F3B")
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
