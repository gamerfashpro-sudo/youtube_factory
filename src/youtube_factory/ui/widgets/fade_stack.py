"""Stacked pages with a short crossfade.

The outgoing page is captured once as a pixmap and shown by a transparent overlay that
fades out above the new page. Live widgets get no graphics effects, so the cost is one
pixmap blit per frame for about 200 ms.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QStackedWidget, QWidget

from youtube_factory.ui.motion import Tween, motion


class _Overlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pixmap: QPixmap | None = None
        self.opacity = 1.0
        self.hide()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.pixmap is None:
            return
        p = QPainter(self)
        p.setOpacity(self.opacity)
        p.drawPixmap(0, 0, self.pixmap)


class FadeStack(QStackedWidget):
    DURATION = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._overlay = _Overlay(self)
        self._fade = Tween(self, value=1.0, on_change=self._step)

    def _step(self) -> None:
        t = self._fade.value
        if t >= 1.0:
            self._overlay.hide()
            self._overlay.pixmap = None
        else:
            self._overlay.opacity = 1.0 - t
            self._overlay.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802 - Qt override
        if index == self.currentIndex():
            return
        animate = motion.enabled and self.isVisible() and self.width() > 0
        if animate:
            self._overlay.pixmap = self.grab()
        super().setCurrentIndex(index)
        if animate:
            self._overlay.setGeometry(self.rect())
            self._overlay.opacity = 1.0
            self._overlay.show()
            self._overlay.raise_()
            self._fade.jump(0.0)
            self._fade.go(1.0, self.DURATION)
