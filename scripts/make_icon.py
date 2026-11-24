"""Generate the application icon (PNG and multi-size ICO) with Pillow.

Usage: python scripts/make_icon.py
Requires: pip install pillow
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SIZE = 1024
SCALE = 4  # supersampling for smooth edges

BG = (20, 20, 22, 255)
VIOLET = (124, 92, 255, 255)
AMBER = (255, 176, 32, 255)


def draw_icon() -> Image.Image:
    s = SIZE * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Rounded dark tile.
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=BG)
    # Tall 9:16 "phone" panel in violet, the Shorts format.
    pw, ph = int(s * 0.44), int(s * 0.78)
    px, py = (s - pw) // 2, (s - ph) // 2
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=int(s * 0.07), fill=VIOLET)
    # Amber play triangle.
    cx, cy = s // 2 + int(s * 0.012), s // 2
    r = int(s * 0.115)
    d.polygon([(cx - r * 0.8, cy - r), (cx - r * 0.8, cy + r), (cx + r * 1.1, cy)], fill=AMBER)
    # Small amber "spark" dot in the corner of the panel.
    dot = int(s * 0.022)
    d.ellipse((px + pw - dot * 4, py + dot * 3, px + pw - dot * 2, py + dot * 5), fill=AMBER)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    icon = draw_icon()
    (ROOT / "assets").mkdir(exist_ok=True)
    resources = ROOT / "src" / "youtube_factory" / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    icon.save(ROOT / "assets" / "icon.png")
    icon.resize((256, 256), Image.LANCZOS).save(resources / "icon.png")
    icon.save(
        ROOT / "assets" / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("Icon files written")


if __name__ == "__main__":
    main()
