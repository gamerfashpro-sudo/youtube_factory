"""Pre-rendered blurred backdrop ("aurora") that glass panels sit on.

Rendered once per size and palette at a fraction of the real resolution; smooth
gradients lose nothing when scaled up, and painting is a single cheap blit.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize
from PySide6.QtGui import QColor, QPainter, QPixmap, QRadialGradient

from youtube_factory.ui.theme import Palette

SCALE = 3
_cache: dict[tuple[str, int, int], QPixmap] = {}


def _render(size: QSize, p: Palette) -> QPixmap:
    w, h = max(1, size.width() // SCALE), max(1, size.height() // SCALE)
    pm = QPixmap(w, h)
    pm.fill(p.base)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    big = max(w, h)
    for blob in p.blobs:
        c = QColor(blob.color)
        c.setAlpha(blob.alpha)
        edge = QColor(c)
        edge.setAlpha(0)
        g = QRadialGradient(blob.x * w, blob.y * h, blob.r * big)
        g.setColorAt(0.0, c)
        g.setColorAt(1.0, edge)
        painter.fillRect(0, 0, w, h, g)
    painter.end()
    return pm


def backdrop_for(size: QSize, p: Palette) -> QPixmap:
    # Quantise the size so a live window resize does not re-render on every pixel.
    key = (p.name, (size.width() // 64 + 1) * 64, (size.height() // 64 + 1) * 64)
    pm = _cache.get(key)
    if pm is None:
        if len(_cache) > 6:
            _cache.clear()
        pm = _render(QSize(key[1], key[2]), p)
        _cache[key] = pm
    return pm


def paint_backdrop(painter: QPainter, area: QRect, window_size: QSize, p: Palette) -> None:
    """Paint the part `area` of a window of `window_size` with the backdrop."""
    pm = backdrop_for(window_size, p)
    sx = pm.width() / max(1, (window_size.width() // 64 + 1) * 64)
    sy = pm.height() / max(1, (window_size.height() // 64 + 1) * 64)
    src = QRectF(area.x() * sx, area.y() * sy, area.width() * sx, area.height() * sy)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawPixmap(QRectF(area), pm, src)
