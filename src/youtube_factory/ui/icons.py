"""Line icons drawn with QPainter paths on a 24x24 grid. No icon fonts or image files."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

# Mini path language: M L H V Q C Z with absolute coordinates, plus
# "O cx cy r" for a circle and "R x y w h r" for a rounded rectangle.
SPECS: dict[str, str] = {
    "home": "M 3 11 L 12 3.5 L 21 11 M 5.5 9.5 V 19.5 Q 5.5 20 6 20 H 18 Q 18.5 20 18.5 19.5 V 9.5"
    " M 10 20 V 14 H 14 V 20",
    "clock": "O 12 12 8.5 M 12 7 V 12 L 15.5 14",
    "sliders": "M 4 6 H 7 M 11.5 6 H 20 M 4 12 H 12.5 M 17 12 H 20 M 4 18 H 6.5 M 11 18 H 20"
    " O 9.2 6 2.2 O 14.8 12 2.2 O 8.8 18 2.2",
    "copy": "R 8.5 8.5 11 11 2.5 M 15.5 8.5 V 6.5 Q 15.5 5 14 5 H 6.5 Q 5 5 5 6.5 V 14 Q 5 15.5 6.5 15.5"
    " H 8.5",
    "edit": "M 4.5 19.5 L 5 15.5 L 15.5 5 Q 16.5 4 17.5 5 L 19 6.5 Q 20 7.5 19 8.5 L 8.5 19 Z"
    " M 13.5 7 L 17 10.5",
    "trash": "M 4 7 H 20 M 9 7 V 4.5 H 15 V 7 M 6 7 L 7 19.5 Q 7 20 7.5 20 H 16.5 Q 17 20 17 19.5 L 18 7"
    " M 10 11 V 16 M 14 11 V 16",
    "play": "M 8 5.5 L 18.5 12 L 8 18.5 Z",
    "folder": "M 3.5 7 Q 3.5 5.5 5 5.5 H 9.5 L 11.5 8 H 19 Q 20.5 8 20.5 9.5 V 17 Q 20.5 18.5 19 18.5"
    " H 5 Q 3.5 18.5 3.5 17 Z",
    "check": "M 5 12.5 L 10 17.5 L 19 7",
    "close": "M 6 6 L 18 18 M 18 6 L 6 18",
    "plus": "M 12 5 V 19 M 5 12 H 19",
    "export": "M 12 4 V 15 M 7.5 10.5 L 12 15 L 16.5 10.5 M 5 19.5 H 19",
    "sparkle": "M 12 3 Q 13 10.5 21 12 Q 13 13.5 12 21 Q 11 13.5 3 12 Q 11 10.5 12 3 Z",
    "text": "M 6.5 3.5 H 14 L 19 8.5 V 19.5 Q 19 20.5 18 20.5 H 6.5 Q 5 20.5 5 19.5 V 5 Q 5 3.5 6.5 3.5"
    " M 14 3.5 V 8.5 H 19 M 8.5 13 H 15.5 M 8.5 16.5 H 13",
    "external": "M 14 4 H 20 V 10 M 20 4 L 11 13 M 18 14 V 18.5 Q 18 20 16.5 20 H 5.5 Q 4 20 4 18.5"
    " V 7.5 Q 4 6 5.5 6 H 10",
    "user": "O 12 8.5 3.5 M 5 20 Q 5 14.5 12 14.5 Q 19 14.5 19 20",
    "film": "R 4 5 16 14 2.5 M 9 5 V 19 M 15 5 V 19 M 4 12 H 9 M 15 12 H 20",
    "alert": "M 12 4 L 21 19.5 H 3 Z M 12 10 V 14 O 12 16.8 0.6",
    "back": "M 19 12 H 5 M 11 6 L 5 12 L 11 18",
    "info": "O 12 12 8.5 M 12 11 V 16.5 O 12 7.9 0.6",
    "link": "M 10 14 L 14 10 M 9 7.5 L 10.5 6 Q 13 3.5 15.5 6 Q 18 8.5 15.5 11 L 14 12.5"
    " M 15 16.5 L 13.5 18 Q 11 20.5 8.5 18 Q 6 15.5 8.5 13 L 10 11.5",
    "paste": "R 6 5 12 15.5 2.5 M 9.5 3.5 H 14.5 V 6.5 H 9.5 Z M 9 11 H 15 M 9 14.5 H 13",
}

FILLED = {"play"}
_cache: dict[str, QPainterPath] = {}


def _build(spec: str) -> QPainterPath:
    path = QPainterPath()
    tokens = iter(spec.split())

    def nums(n: int) -> list[float]:
        return [float(next(tokens)) for _ in range(n)]

    for tok in tokens:
        if tok == "M":
            path.moveTo(*nums(2))
        elif tok == "L":
            path.lineTo(*nums(2))
        elif tok == "H":
            path.lineTo(nums(1)[0], path.currentPosition().y())
        elif tok == "V":
            path.lineTo(path.currentPosition().x(), nums(1)[0])
        elif tok == "Q":
            path.quadTo(*nums(4))
        elif tok == "C":
            path.cubicTo(*nums(6))
        elif tok == "Z":
            path.closeSubpath()
        elif tok == "O":
            cx, cy, r = nums(3)
            path.addEllipse(QPointF(cx, cy), r, r)
        elif tok == "R":
            x, y, w, h, r = nums(5)
            path.addRoundedRect(QRectF(x, y, w, h), r, r)
    return path


def _star() -> QPainterPath:
    path = QPainterPath()
    cx, cy, outer, inner = 12.0, 12.8, 9.4, 4.0
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / 5
        pt = QPointF(cx + r * math.cos(a), cy + r * math.sin(a))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    return path


def _path(name: str) -> QPainterPath:
    if name not in _cache:
        _cache[name] = _star() if name in ("star", "star_fill") else _build(SPECS[name])
    return _cache[name]


def paint_icon(
    p: QPainter,
    name: str,
    rect: QRectF,
    color: QColor,
    width: float = 1.7,
    filled: bool = False,
) -> None:
    """Draw icon `name` scaled into `rect`. `filled` fills the shape as well."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.topLeft())
    s = min(rect.width(), rect.height()) / 24.0
    p.scale(s, s)
    pen = QPen(
        color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
    )
    p.setPen(pen)
    if filled or name in FILLED or name == "star_fill":
        p.setBrush(color)
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(_path(name))
    p.restore()
