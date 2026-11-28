"""Non-blocking notification pill that slides up from the bottom edge of the window."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget

from youtube_factory.ui.fonts import font
from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, with_alpha
from youtube_factory.ui.theme import theme
from youtube_factory.ui.widgets.glass import paint_glass

H = 48


class Toast(QWidget):
    DURATION_MS = 3200

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._text = ""
        self._error = False
        self._t = Tween(self, on_change=self._step)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self._t.go(0.0, 260))
        self.setFont(font(14, "medium"))
        self.hide()

    def text(self) -> str:
        return self._text

    def show_message(self, text: str, error: bool = False) -> None:
        self._text, self._error = text, error
        avail = max(240, self.parentWidget().width() - 80)
        fm = QFontMetrics(self.font())
        shown = fm.elidedText(text, Qt.TextElideMode.ElideRight, avail - 80)
        self._shown = shown
        w = min(avail, fm.horizontalAdvance(shown) + 76)
        self.resize(QSize(w, H))
        self.show()
        self.raise_()
        self._t.go(1.0, 320)
        self._timer.start(self.DURATION_MS)
        self._place()

    def _step(self) -> None:
        self._place()
        if self._t.value <= 0.0 and not self._t.running:
            self.hide()
        self.update()

    def _place(self) -> None:
        parent = self.parentWidget()
        rise = (1.0 - self._t.value) * 22
        self.move((parent.width() - self.width()) // 2, int(parent.height() - H - 96 + rise))

    def reposition(self) -> None:
        self._place()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setOpacity(self._t.value)
        r = QRectF(self.rect())
        paint_glass(
            p,
            r,
            H / 2,
            strength=2.6 if pal.dark else 1.6,
            tint=with_alpha(pal.danger if self._error else pal.accent, 70),
        )
        color = pal.danger if self._error else pal.success
        paint_icon(
            p, "alert" if self._error else "check", QRectF(18, (H - 20) / 2, 20, 20), color, 2.0
        )
        p.setFont(self.font())
        p.setPen(pal.text)
        p.drawText(
            QRectF(48, 0, r.width() - 60, H),
            Qt.AlignmentFlag.AlignVCenter,
            getattr(self, "_shown", self._text),
        )
