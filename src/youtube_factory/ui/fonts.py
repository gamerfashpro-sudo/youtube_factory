"""Bundled Golos Text font (SIL OFL) with a Segoe UI fallback."""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase

from youtube_factory.data.paths import resource_dir

log = logging.getLogger(__name__)

_FAMILIES = {
    "regular": "Golos Text",
    "medium": "Golos Text Medium",
    "semibold": "Golos Text SemiBold",
    "bold": "Golos Text",
}
_FALLBACK_WEIGHT = {
    "regular": QFont.Weight.Normal,
    "medium": QFont.Weight.Medium,
    "semibold": QFont.Weight.DemiBold,
    "bold": QFont.Weight.Bold,
}
_loaded = False


def load_fonts() -> bool:
    """Register the bundled fonts. Returns False if none could be loaded."""
    global _loaded
    folder = resource_dir() / "fonts"
    ids = [QFontDatabase.addApplicationFont(str(f)) for f in sorted(folder.glob("*.ttf"))]
    _loaded = any(i >= 0 for i in ids)
    if not _loaded:
        log.warning("Bundled fonts were not loaded, falling back to Segoe UI")
    return _loaded


def font(px: int, weight: str = "regular") -> QFont:
    """Return a font with the given pixel size and weight name."""
    if _loaded:
        f = QFont(_FAMILIES[weight])
        if weight == "bold":
            f.setBold(True)
    else:
        f = QFont("Segoe UI")
        f.setWeight(_FALLBACK_WEIGHT[weight])
    f.setPixelSize(px)
    return f


def app_font() -> QFont:
    """Default application font."""
    return font(14, "regular")
