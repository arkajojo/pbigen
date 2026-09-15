"""Extract the reusable design shell from a shared Power BI ``.pbix``.

A ``.pbix`` is a zip archive. This pulls out the pieces you can legitimately reuse to match a
report's *look* — its custom theme (colours, fonts, visual styles) and its images (logo,
background) — so you can regenerate your own data into the same shell:

    pbigen extract-template their_report.pbix --out template
    pbigen generate --source ... --theme template/theme.json --logo template/assets/<logo> --nav right

It does not copy their visuals or data (those follow your own data). If the report only used a
built-in theme, there is no custom theme file to extract — the layout knobs (``--nav``, ``--logo``,
``--canvas``) still let you match the shell.

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, field

_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"}


@dataclass
class Extracted:
    theme_path: str | None = None
    theme_source: str | None = None
    images: list[str] = field(default_factory=list)


def _looks_like_theme(obj: object) -> bool:
    return isinstance(obj, dict) and ("dataColors" in obj or "visualStyles" in obj)


def extract_template(pbix_path: str, out_dir: str) -> Extracted:
    """Extract the custom theme and images from ``pbix_path`` into ``out_dir``."""
    if not os.path.exists(pbix_path):
        raise FileNotFoundError(pbix_path)
    assets = os.path.join(out_dir, "assets")
    os.makedirs(assets, exist_ok=True)
    result = Extracted()

    with zipfile.ZipFile(pbix_path) as z:
        for name in z.namelist():
            low = name.lower()
            if low.endswith("/"):
                continue
            # a custom theme JSON registered in the report's static resources
            if low.endswith(".json") and "registeredresources" in low:
                try:
                    obj = json.loads(z.read(name).decode("utf-8-sig"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if _looks_like_theme(obj) and result.theme_path is None:
                    result.theme_path = os.path.join(out_dir, "theme.json")
                    result.theme_source = name
                    with open(result.theme_path, "w", encoding="utf-8") as fh:
                        json.dump(obj, fh, indent=2)
            # images (logo / background) bundled with the report
            elif os.path.splitext(low)[1] in _IMG_EXT and "staticresources" in low:
                dst = os.path.join(assets, os.path.basename(name))
                with open(dst, "wb") as fh:
                    fh.write(z.read(name))
                result.images.append(os.path.basename(name))

    return result
