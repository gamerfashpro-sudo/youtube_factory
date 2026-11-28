"""Text inputs with glass background and animated focus ring."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QFocusEvent, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QWidget

from youtube_factory.ui.fonts import font
from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, mix, with_alpha
from youtube_factory.ui.theme import R_FIELD, theme
from youtube_factory.ui.widgets.glow import paint_inner_glow


def _paint_field(p: QPainter, rect: QRectF, focus: float, radius: float) -> None:
    pal = theme.p
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(pal.field)
    p.drawRoundedRect(rect, radius, radius)
    base = with_alpha(pal.text, 26 if pal.dark else 34)
    p.setPen(QPen(mix(base, pal.accent_hi, focus), 1.0 + focus * 0.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
    if focus > 0.01:
        paint_inner_glow(p, rect, radius, pal.accent_hi, 12, int((70 if pal.dark else 55) * focus))


class GlassLineEdit(QLineEdit):
    def __init__(
        self,
        placeholder: str = "",
        icon: str | None = None,
        height: int = 44,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self._focus = Tween(self)
        self.setFont(font(14, "regular"))
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self.setTextMargins(40 if icon else 14, 0, 14, 0)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt override
        self._focus.go(1.0, 160)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt override
        self._focus.go(0.0, 220)
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        if not self.isEnabled():
            p.setOpacity(0.55)
        r = QRectF(self.rect())
        _paint_field(p, r, self._focus.value, R_FIELD)
        if self._icon:
            pal = theme.p
            paint_icon(
                p,
                self._icon,
                QRectF(14, (r.height() - 18) / 2, 18, 18),
                mix(pal.faint, pal.accent_hi, self._focus.value),
                1.7,
            )
        p.end()
        super().paintEvent(event)


class GlassTextEdit(QPlainTextEdit):
    def __init__(self, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._focus = Tween(self, on_change=self.viewport().update)
        self.setFont(font(14, "regular"))
        self.setPlaceholderText(placeholder)
        self.document().setDocumentMargin(12)
        self.viewport().setAutoFillBackground(False)
        self.viewport().installEventFilter(self)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt override
        self._focus.go(1.0, 160)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt override
        self._focus.go(0.0, 220)
        super().focusOutEvent(event)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt override
        # Paint the glass under the text before QPlainTextEdit draws on the viewport.
        if obj is self.viewport() and event.type() == QEvent.Type.Paint:
            p = QPainter(self.viewport())
            _paint_field(p, QRectF(self.viewport().rect()), self._focus.value, R_FIELD)
            p.end()
        return super().eventFilter(obj, event)
