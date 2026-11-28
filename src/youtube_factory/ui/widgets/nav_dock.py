"""Floating glass navigation dock with a sliding selection pill."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QVBoxLayout, QWidget

from youtube_factory import __version__
from youtube_factory.ui.fonts import font
from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, mix, with_alpha
from youtube_factory.ui.theme import R_DOCK, theme
from youtube_factory.ui.widgets.common import make_label
from youtube_factory.ui.widgets.glass import GlassPanel, paint_glass


class NavItem(QAbstractButton):
    def __init__(self, text: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self.setText(text)
        self.setCheckable(True)
        self.setFont(font(15, "medium"))
        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._hover = Tween(self)
        self._on = Tween(self)
        self.toggled.connect(lambda on: self._on.go(1.0 if on else 0.0, 220))

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(160, 46)

    def enterEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(1.0, 140)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(0.0, 240)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h, on = self._hover.value, self._on.value
        r = QRectF(self.rect())
        if h and on < 1.0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(with_alpha(pal.text, int(16 * h * (1.0 - on))))
            p.drawRoundedRect(r, 16, 16)
        color = mix(pal.muted, pal.text, max(on, h * 0.8))
        shift = 2.0 * h * (1.0 - on)
        paint_icon(
            p,
            self._icon,
            QRectF(16 + shift, (r.height() - 22) / 2, 22, 22),
            mix(color, pal.accent_hi, on * 0.8),
            1.8,
        )
        p.setFont(self.font())
        p.setPen(color)
        p.drawText(
            QRectF(50 + shift, 0, r.width() - 56, r.height()),
            Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 16, 16)


class NavDock(GlassPanel):
    WIDTH = 208

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, radius=R_DOCK, strength=1.0)
        self.setFixedWidth(self.WIDTH)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.items: dict[int, NavItem] = {}
        self._pill = Tween(self)
        self._pill_h = 46.0
        self._current: NavItem | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 22, 14, 18)
        lay.setSpacing(6)
        self.brand = make_label("YouTube Factory", role="h2")
        lay.addWidget(self.brand)
        lay.addSpacing(16)
        self._lay = lay
        lay.addStretch(1)
        self.version = make_label(f"v{__version__}", role="small")
        lay.addWidget(self.version)

    def add_item(self, page: int, text: str, icon: str) -> NavItem:
        item = NavItem(text, icon, self)
        self._group.addButton(item)
        self.items[page] = item
        self._lay.insertWidget(self._lay.count() - 2, item)
        return item

    def set_current(self, page: int) -> None:
        item = self.items[page]
        item.setChecked(True)
        self._current = item
        self._move_pill(animate=True)

    def _move_pill(self, animate: bool) -> None:
        if self._current is None:
            return
        y = float(self._current.y())
        if animate:
            self._pill.go(y, 280)
        else:
            self._pill.jump(y)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._lay.activate()
        self._move_pill(animate=False)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        paint_glass(p, QRectF(self.rect()), self.radius, strength=1.0)
        if self._current is not None:
            pal = theme.p
            r = QRectF(14, self._pill.value, self.width() - 28, self._pill_h)
            paint_glass(p, r, 16, strength=1.6, tint=with_alpha(pal.accent, 70))
