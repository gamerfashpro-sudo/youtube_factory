"""Non-blocking toast notification shown at the bottom of the window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from youtube_factory.ui.theme import Palette


class Toast(QLabel):
    DURATION_MS = 3200

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._palette: Palette | None = None
        self.hide()

    def apply_palette(self, palette: Palette) -> None:
        self._palette = palette

    def show_message(self, text: str, error: bool = False) -> None:
        p = self._palette
        bg = (p.danger if error else p.accent) if p else "#7C5CFF"
        self.setStyleSheet(
            f"background: {bg}; color: #FFFFFF; border-radius: 12px; padding: 12px 20px;"
            " font-weight: 600;"
        )
        self.setText(text)
        self.setFixedWidth(min(520, max(240, self.parentWidget().width() - 80)))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(self.DURATION_MS)

    def reposition(self) -> None:
        parent = self.parentWidget()
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._hide_after_fade)
        self._anim.start()

    def _hide_after_fade(self) -> None:
        self._anim.finished.disconnect(self._hide_after_fade)
        if self._effect.opacity() <= 0.01:
            self.hide()
