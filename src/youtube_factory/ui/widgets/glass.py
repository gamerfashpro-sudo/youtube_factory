"""Glass surface painting and the basic panel widget."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QWidget

from youtube_factory.ui.motion import Tween, with_alpha
from youtube_factory.ui.theme import R_PANEL, theme


def paint_glass(
    p: QPainter,
    rect: QRectF,
    radius: float,
    hover: float = 0.0,
    strength: float = 1.0,
    tint: QColor | None = None,
) -> None:
    """Translucent panel: soft vertical fill, lit edge and a thin specular line on top."""
    pal = theme.p
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    top, bottom = QColor(pal.glass_a), QColor(pal.glass_b)
    boost = int(16 * hover)
    top.setAlpha(min(255, int(top.alpha() * strength) + boost))
    bottom.setAlpha(min(255, int(bottom.alpha() * strength) + boost // 2))
    fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    fill.setColorAt(0.0, top)
    fill.setColorAt(1.0, bottom)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, radius, radius)

    if tint is not None:
        p.setBrush(tint)
        p.drawRoundedRect(rect, radius, radius)

    hi = QColor(pal.stroke_hi)
    hi.setAlpha(min(255, hi.alpha() + int(70 * hover)))
    edge = QLinearGradient(rect.topLeft(), rect.bottomRight())
    edge.setColorAt(0.0, hi)
    edge.setColorAt(0.5, pal.stroke_lo)
    edge.setColorAt(1.0, with_alpha(hi, hi.alpha() // 3))
    p.setPen(QPen(edge, 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    inner = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    p.drawRoundedRect(inner, radius - 0.5, radius - 0.5)

    if radius >= 10:
        line = QLinearGradient(rect.left() + radius, 0, rect.right() - radius, 0)
        shine = QColor(255, 255, 255, 46 if pal.dark else 150)
        line.setColorAt(0.0, with_alpha(shine, 0))
        line.setColorAt(0.5, shine)
        line.setColorAt(1.0, with_alpha(shine, 0))
        p.setPen(QPen(line, 1.0))
        y = rect.top() + 1.5
        p.drawLine(QPointF(rect.left() + radius, y), QPointF(rect.right() - radius, y))


class GlassPanel(QFrame):
    """A rounded translucent container. Optionally brightens its edge on hover."""

    def __init__(
        self,
        parent: QWidget | None = None,
        radius: float = R_PANEL,
        hoverable: bool = False,
        strength: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self.radius = radius
        self.strength = strength
        self._hoverable = hoverable
        self._hover = Tween(self)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def enterEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        if self._hoverable:
            self._hover.go(1.0, 160)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        if self._hoverable:
            self._hover.go(0.0, 260)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        paint_glass(p, QRectF(self.rect()), self.radius, self._hover.value, self.strength)
