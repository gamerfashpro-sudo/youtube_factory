"""Soft glow ("bloom") painted with a few translucent strokes, no blur effects.

Cheap on purpose: a halo is a handful of rounded-rect strokes, repainted only while the
widget it belongs to is animating.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from youtube_factory.ui.theme import theme

HALO_MARGIN = 16  # how far the halo reaches beyond its button, in pixels


def paint_glow(
    p: QPainter, rect: QRectF, radius: float, color: QColor, spread: float, alpha: int
) -> None:
    """Halo around `rect`: stacked strokes that fade quadratically with the distance."""
    if alpha <= 0 or spread <= 0:
        return
    steps = max(2, int(spread // 2))
    width = spread / steps
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(steps):
        grow = (i + 0.5) * width
        fade = (1.0 - (i + 0.5) / steps) ** 2
        c = QColor(color)
        c.setAlpha(int(alpha * fade))
        if not c.alpha():
            continue
        p.setPen(QPen(c, width + 0.6))
        p.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), radius + grow, radius + grow)


def paint_inner_glow(
    p: QPainter, rect: QRectF, radius: float, color: QColor, depth: float, alpha: int
) -> None:
    """Light that seems to come from the edge of `rect` and fades toward the middle."""
    if alpha <= 0 or depth <= 0:
        return
    steps = max(2, int(depth // 2))
    width = depth / steps
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(steps):
        inset = (i + 0.5) * width
        c = QColor(color)
        c.setAlpha(int(alpha * (1.0 - (i + 0.5) / steps) ** 2))
        if not c.alpha():
            continue
        p.setPen(QPen(c, width + 0.6))
        p.drawRoundedRect(
            rect.adjusted(inset, inset, -inset, -inset),
            max(1.0, radius - inset),
            max(1.0, radius - inset),
        )


class GlowHalo(QWidget):
    """Transparent widget sitting right under a primary button and glowing around it.

    It is a sibling of the button (a widget cannot paint outside its own rectangle), so it
    never changes the layout and never takes mouse events.
    """

    def __init__(self, button: QWidget, parent: QWidget) -> None:
        super().__init__(parent)
        self._button = button
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.installEventFilter(self)
        button.destroyed.connect(self._button_gone)
        self.sync()

    def _button_gone(self) -> None:
        self.hide()  # right away: a pending repaint must not touch the dead button
        self.deleteLater()

    def sync(self) -> None:
        """Follow the button: same place, same visibility, directly below it."""
        b = self._button
        if not isValid(b):
            return
        want = b.isVisibleTo(self.parentWidget()) and b.isEnabled() and b.variant == "primary"
        self.setGeometry(
            b.geometry().adjusted(-HALO_MARGIN, -HALO_MARGIN, HALO_MARGIN, HALO_MARGIN)
        )
        self.stackUnder(b)
        self.setVisible(want)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        if event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.EnabledChange,
            QEvent.Type.ParentChange,
        ):
            self.sync()
        return False

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        b = self._button
        if not isValid(b):
            return
        pal = theme.p
        hover = b._hover.value  # noqa: SLF001 - the halo is a part of the button
        press = b._press.value  # noqa: SLF001
        base, lift = (84, 96) if pal.dark else (60, 70)
        alpha = int((base + lift * hover) * (1.0 - 0.35 * press))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inner = QRectF(self.rect()).adjusted(HALO_MARGIN, HALO_MARGIN, -HALO_MARGIN, -HALO_MARGIN)
        radius = 12.0 if b.height() > 36 else 10.0
        paint_glow(p, inner, radius, pal.accent_hi, HALO_MARGIN * (0.8 + 0.2 * hover), alpha)
        p.end()
