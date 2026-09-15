"""Render assets/social-preview.png — the 1280x640 GitHub social card.

Deterministic (Pillow), so text metrics and layout are exact regardless of installed SVG fonts.
Run:  python scripts/make_social_preview.py

Author: Arka Gupta
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "assets", "social-preview.png")

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

INK = (174, 182, 214)       # tagline
MUTED = (110, 119, 168)     # sub line


def gradient(size, c0, c1, horizontal=True):
    """A smooth two-stop gradient via a 2px source upscaled (bilinear)."""
    small = Image.new("RGB", (2, 1) if horizontal else (1, 2))
    small.putpixel((0, 0), c0)
    small.putpixel((1, 0) if horizontal else (0, 1), c1)
    return small.resize(size, Image.BICUBIC)


def diagonal(size, tl, tr, bl, br):
    small = Image.new("RGB", (2, 2))
    small.putpixel((0, 0), tl)
    small.putpixel((1, 0), tr)
    small.putpixel((0, 1), bl)
    small.putpixel((1, 1), br)
    return small.resize(size, Image.BICUBIC)


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def gradient_text(text, font, c0, c1):
    """Return an RGBA image of `text` filled with a horizontal gradient."""
    x0, y0, x1, y1 = font.getbbox(text)
    tw, th = x1 - x0, y1 - y0
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).text((-x0, -y0), text, font=font, fill=255)
    grad = gradient((tw, th), c0, c1).convert("RGBA")
    grad.putalpha(mask)
    return grad


def main() -> None:
    banner = diagonal((W, H), (0x12, 0x15, 0x2E), (0x14, 0x18, 0x33),
                      (0x16, 0x1B, 0x37), (0x1B, 0x1F, 0x3B)).convert("RGBA")
    draw = ImageDraw.Draw(banner)

    # --- right-side decorative mini dashboard (subtle) ---
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    dd.rounded_rectangle([812, 150, 1192, 486], radius=20, fill=(255, 255, 255, 12))
    dd.rounded_rectangle([838, 176, 948, 236], radius=10, fill=(76, 111, 255, 90))
    dd.rounded_rectangle([962, 176, 1072, 236], radius=10, fill=(34, 193, 195, 90))
    dd.rounded_rectangle([1086, 176, 1176, 236], radius=10, fill=(253, 187, 45, 90))
    pts = [(838, 388), (888, 344), (938, 360), (988, 306), (1038, 328), (1088, 286), (1138, 300), (1176, 268)]
    dd.line(pts, fill=(143, 176, 255, 150), width=5, joint="curve")
    for i, (bx, bh) in enumerate([(842, 52), (900, 74), (958, 40), (1016, 62), (1074, 48), (1132, 70)]):
        dd.rounded_rectangle([bx, 466 - bh, bx + 42, 466], radius=6, fill=(143, 176, 255, 70))
    banner.alpha_composite(deco)

    # --- icon tile ---
    tile_xy, tile_wh, tile_r = (96, 205), (170, 170), 42
    tile = gradient(tile_wh, (0x2B, 0x2F, 0x6B), (0x4C, 0x6F, 0xFF)).convert("RGBA")
    banner.paste(tile, tile_xy, rounded_mask(tile_wh, tile_r))
    tx, ty = tile_xy

    def bar(cx, top, w, color):
        draw.rounded_rectangle([tx + cx, ty + top, tx + cx + w, ty + 132], radius=6, fill=color)
    bar(44, 96, 21, (34, 193, 195, 255))
    bar(74, 66, 21, (143, 176, 255, 255))
    bar(104, 40, 21, (255, 255, 255, 255))
    draw.ellipse([tx + 108, ty + 24, tx + 126, ty + 42], fill=(253, 187, 45, 255))

    # --- wordmark (gradient), vertically centered on the tile ---
    word_font = ImageFont.truetype(BOLD, 104)
    word = gradient_text("pbigen", word_font, (0x4C, 0x6F, 0xFF), (0x22, 0xC1, 0xC3))
    wy = tile_xy[1] + (tile_wh[1] - word.height) // 2 - 6
    banner.alpha_composite(word, (300, wy))

    # --- tagline + sub line ---
    draw.text((302, 398), "Generate world-class Power BI dashboards", font=ImageFont.truetype(REG, 30), fill=INK)
    draw.text((302, 438), "from any data source.", font=ImageFont.truetype(REG, 30), fill=INK)
    draw.text((302, 492), "16 sources  ·  deterministic or LLM  ·  MIT open source",
              font=ImageFont.truetype(BOLD, 21), fill=MUTED)

    banner.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({banner.width}x{banner.height})")


if __name__ == "__main__":
    main()
