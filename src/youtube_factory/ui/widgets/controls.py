"""Buttons, segmented control, switch, check box and chips.

Every control keeps a small Tween for hover and press, so it glides between states
and repaints only its own rectangle.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QAbstractButton, QWidget

from youtube_factory.ui.fonts import font
from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, mix, with_alpha
from youtube_factory.ui.theme import R_CONTROL, theme
from youtube_factory.ui.widgets.glass import paint_glass
from youtube_factory.ui.widgets.glow import GlowHalo

ICON = 18
GAP = 8


class GlassButton(QAbstractButton):
    """Button with variants: primary, secondary, ghost and danger. Icon and text optional."""

    def __init__(
        self,
        text: str = "",
        variant: str = "secondary",
        icon: str | None = None,
        tooltip: str = "",
        height: int = 40,
        square: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._variant = variant
        self._halo: GlowHalo | None = None
        self._flash_icon: str | None = None
        self._icon = icon
        self._square = square
        self._height = 36 if square else height
        self._active = False
        self.setText(text)
        self.setFont(font(14, "medium"))
        if tooltip:
            self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._hover = Tween(self, on_change=self._repaint_all)
        self._press = Tween(self, on_change=self._repaint_all)
        self._pop = Tween(self)
        self.setFixedHeight(self._height)

    # --- state ---------------------------------------------------------------
    @property
    def variant(self) -> str:
        return self._variant

    @variant.setter
    def variant(self, value: str) -> None:
        self._variant = value
        self._sync_halo()
        self.update()

    def _repaint_all(self) -> None:
        self.update()
        if self._halo is not None and self._halo.isVisible():
            self._halo.update()

    def _sync_halo(self) -> None:
        """Primary buttons glow; the halo is made once the button has a parent."""
        parent = self.parentWidget()
        if self._variant != "primary" and self._halo is None:
            return
        if parent is None:
            return
        if self._halo is None or self._halo.parentWidget() is not parent:
            if self._halo is not None:
                self._halo.deleteLater()
            self._halo = GlowHalo(self, parent)
        else:
            self._halo.sync()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._sync_halo()
        super().showEvent(event)

    def set_active(self, active: bool, animate: bool = False) -> None:
        """Highlight the button (used by the favourite star)."""
        changed = active != self._active
        self._active = active
        if changed and animate:
            self._pop.jump(0.0)
            self._pop.go(1.0, 320)
        self.update()

    def flash_done(self, ms: int = 1300) -> None:
        """Show a green check mark for a moment: the click did something."""
        if self._flash_icon is None:
            self._flash_icon = self._icon or ""
        self._icon = "check"
        self._pop.jump(0.0)
        self._pop.go(1.0, 320)
        QTimer.singleShot(ms, self, self._end_flash)
        self.update()

    def _end_flash(self) -> None:
        if self._flash_icon is None:
            return
        self._icon = self._flash_icon or None
        self._flash_icon = None
        self.update()

    def set_icon_name(self, icon: str) -> None:
        self._icon = icon
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        if self._square:
            return QSize(self._height, self._height)
        text_w = QFontMetrics(self.font()).horizontalAdvance(self.text()) if self.text() else 0
        icon_w = ICON + (GAP if text_w else 0) if self._icon else 0
        pad = 22 if self.variant == "primary" else 16
        return QSize(pad * 2 + icon_w + text_w, self._height)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return self.sizeHint()

    # --- events --------------------------------------------------------------
    def enterEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(1.0, 140)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(0.0, 240)
        self._press.go(0.0, 160)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._press.go(1.0, 80)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        self._press.go(0.0, 200)
        super().mouseReleaseEvent(event)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        if event.type() == QEvent.Type.EnabledChange:
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if self.isEnabled()
                else Qt.CursorShape.ArrowCursor
            )
        super().changeEvent(event)

    # --- painting ------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            p.setOpacity(0.45)
        h, pr = self._hover.value, self._press.value
        rect = QRectF(self.rect())
        radius = R_CONTROL if self._height > 36 else 10
        if self._square:
            radius = 10

        if self.variant == "primary":
            top = mix(pal.accent_hi, QColor("white"), 0.10 * h)
            bottom = mix(pal.accent_lo, pal.accent, 0.5 * h)
            top, bottom = (
                mix(top, QColor("black"), 0.14 * pr),
                mix(bottom, QColor("black"), 0.14 * pr),
            )
            g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            g.setColorAt(0.0, top)
            g.setColorAt(1.0, bottom)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(rect, radius, radius)
            edge = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            edge.setColorAt(0.0, QColor(255, 255, 255, int(110 + 60 * h)))
            edge.setColorAt(1.0, QColor(255, 255, 255, 24))
            p.setPen(QPen(edge, 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)
            fg = pal.on_accent
        elif self.variant == "secondary":
            paint_glass(p, rect, radius, hover=h, strength=1.1)
            if pr:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 0, 0, int(34 * pr)))
                p.drawRoundedRect(rect, radius, radius)
            fg = pal.text
        else:  # ghost and danger
            base = pal.danger if self.variant == "danger" else pal.text
            fill = with_alpha(base, int((30 if self.variant == "danger" else 22) * h + 14 * pr))
            if fill.alpha():
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(fill)
                p.drawRoundedRect(rect, radius, radius)
            if self.variant == "danger":
                fg = mix(pal.muted, pal.danger, 0.55 + 0.45 * h)
            else:
                fg = mix(pal.muted, pal.text, h)

        if self._active:
            fg = pal.amber
        if self._flash_icon is not None:
            fg = pal.success

        # Content: lifts 1px on hover, sinks 1px on press, pops after toggling.
        dy = -1.0 * h + 1.0 * pr
        scale = 1.0 + 0.22 * _bump(self._pop.value) if self._pop.value else 1.0 - 0.04 * pr
        p.translate(rect.center().x(), rect.center().y() + dy)
        p.scale(scale, scale)
        text = self.text()
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(text) if text else 0
        icon_w = ICON if self._icon else 0
        total = icon_w + (GAP if text_w and icon_w else 0) + text_w
        x = -total / 2
        if self._icon:
            ir = QRectF(x, -ICON / 2, ICON, ICON)
            paint_icon(p, self._icon, ir, fg, 1.7, filled=self._active and self._icon == "star")
            x += ICON + GAP
        if text:
            p.setFont(self.font())
            p.setPen(fg)
            p.drawText(
                QRectF(x, -rect.height() / 2, text_w + 2, rect.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )
        p.resetTransform()

        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)


def _bump(t: float) -> float:
    """0 -> 1 -> 0 hump used for the toggle pop."""
    return 1.0 - abs(2.0 * t - 1.0) if 0.0 < t < 1.0 else 0.0


def icon_button(icon: str, tooltip: str, variant: str = "ghost") -> GlassButton:
    return GlassButton("", variant, icon, tooltip, square=True)


class Segmented(QWidget):
    """Pill selector with a highlight that slides between options."""

    currentChanged = Signal(int)  # noqa: N815 - Qt naming

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._index = 0
        self._pos = Tween(self)
        self._hover_index = -1
        self.setFont(font(14, "medium"))
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setMouseTracking(True)

    # --- QComboBox-like API ----------------------------------------------------
    def addItem(self, text: str, data: object = None) -> None:  # noqa: N802
        self._items.append((text, data))
        self.updateGeometry()
        self.update()

    def count(self) -> int:
        return len(self._items)

    def currentIndex(self) -> int:  # noqa: N802
        return self._index

    def currentData(self) -> object:  # noqa: N802
        return self._items[self._index][1] if self._items else None

    def findData(self, data: object) -> int:  # noqa: N802
        for i, (_, d) in enumerate(self._items):
            if d == data:
                return i
        return -1

    def setCurrentIndex(self, index: int, animate: bool = True) -> None:  # noqa: N802
        index = max(0, min(index, len(self._items) - 1))
        if index == self._index:
            return
        self._index = index
        self._pos.go(float(index), 240) if animate else self._pos.jump(float(index))
        self.currentChanged.emit(index)

    def set_index_silently(self, index: int) -> None:
        self._index = max(0, min(index, len(self._items) - 1))
        self._pos.jump(float(self._index))

    # --- geometry --------------------------------------------------------------
    def _seg_width(self) -> float:
        fm = QFontMetrics(self.font())
        widest = max((fm.horizontalAdvance(t) for t, _ in self._items), default=40)
        return float(widest + 36)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(int(self._seg_width() * max(1, len(self._items)) + 8), 40)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return self.sizeHint()

    def _index_at(self, x: float) -> int:
        w = self._seg_width()
        return int((x - 4) // w) if 4 <= x < 4 + w * len(self._items) else -1

    # --- events ----------------------------------------------------------------
    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        i = self._index_at(event.position().x())
        if i != self._hover_index:
            self._hover_index = i
            self.update()

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        i = self._index_at(event.position().x())
        if i >= 0:
            self.setCurrentIndex(i)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self.setCurrentIndex(self._index + 1)
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self.setCurrentIndex(self._index - 1)
        else:
            super().keyPressEvent(event)

    # --- painting --------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        p.setPen(QPen(with_alpha(pal.text, 22 if pal.dark else 30), 1.0))
        p.setBrush(pal.field)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 20, 20)

        w = self._seg_width()
        pill = QRectF(4 + w * self._pos.value, 4, w, rect.height() - 8)
        paint_glass(p, pill, 16, strength=1.7, tint=with_alpha(pal.accent, 64))

        p.setFont(self.font())
        for i, (text, _) in enumerate(self._items):
            cell = QRectF(4 + w * i, 4, w, rect.height() - 8)
            near = max(0.0, 1.0 - abs(self._pos.value - i))
            color = mix(pal.muted, pal.text, max(near, 0.5 if i == self._hover_index else 0.0))
            p.setPen(color)
            p.drawText(cell, Qt.AlignmentFlag.AlignCenter, text)
        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 20, 20)


class Switch(QAbstractButton):
    """On/off toggle with a gliding knob."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._t = Tween(self)
        self.toggled.connect(lambda on: self._t.go(1.0 if on else 0.0, 200))

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt override
        super().setChecked(checked)
        self._t.jump(1.0 if checked else 0.0)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._t.value
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        track = mix(with_alpha(pal.text, 40), pal.accent, t)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * t
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))
        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-0.5, -0.5, 0.5, 0.5), 13, 13)


class CheckPill(QAbstractButton):
    """Small selection box with an animated tick (used to pick Shorts for export)."""

    def __init__(self, tooltip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._t = Tween(self)
        self._hover = Tween(self)
        self.toggled.connect(lambda on: self._t.go(1.0 if on else 0.0, 180))

    def enterEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(1.0, 120)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(0.0, 200)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t, h = self._t.value, self._hover.value
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        p.setBrush(mix(with_alpha(pal.text, 14 + int(14 * h)), pal.accent, t))
        p.setPen(QPen(mix(with_alpha(pal.text, 70 + int(60 * h)), pal.accent_hi, t), 1.2))
        p.drawRoundedRect(r, 6, 6)
        if t > 0.02:
            paint_icon(
                p, "check", r.adjusted(2, 2, -2, -2), with_alpha(pal.on_accent, int(255 * t)), 2.4
            )
        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)


class Chip(QWidget):
    """Compact rounded label with an optional icon. kind: meta, tag, time."""

    def __init__(
        self,
        text: str = "",
        kind: str = "meta",
        icon: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.kind = kind
        self._icon = icon
        self._text = text
        self.setFont(font(12, "medium"))
        self.setFixedHeight(26)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())

    def setText(self, text: str) -> None:  # noqa: N802
        self._text = text
        self.updateGeometry()
        self.update()

    def text(self) -> str:
        return self._text

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        w = QFontMetrics(self.font()).horizontalAdvance(self._text) + 20
        if self._icon:
            w += 16 + 5
        return QSize(w, 26)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return self.sizeHint()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.kind == "tag":
            bg, fg = with_alpha(pal.accent, 40), pal.accent_hi if pal.dark else pal.accent
        elif self.kind == "time":
            bg, fg = with_alpha(pal.accent, 56), pal.text
        else:
            bg, fg = with_alpha(pal.text, 18 if pal.dark else 20), pal.muted
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        x = 10.0
        if self._icon:
            paint_icon(p, self._icon, QRectF(x - 1, (r.height() - 16) / 2, 16, 16), fg, 1.7)
            x += 16 + 4
        p.setFont(self.font())
        p.setPen(fg)
        p.drawText(
            QRectF(x, 0, r.width() - x, r.height()), Qt.AlignmentFlag.AlignVCenter, self._text
        )


class ActionTile(QAbstractButton):
    """Large glass tile with an icon, a title and one line of explanation."""

    def __init__(self, title: str, subtitle: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title, self._subtitle, self._icon = title, subtitle, icon
        self.setText(title)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedHeight(92)
        self.setMinimumWidth(240)
        self._hover = Tween(self)
        self._press = Tween(self)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(320, 92)

    def enterEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(1.0, 160)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt override
        self._hover.go(0.0, 260)
        self._press.go(0.0, 160)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        self._press.go(1.0, 80)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        self._press.go(0.0, 200)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h, pr = self._hover.value, self._press.value
        r = QRectF(self.rect()).adjusted(0, 0, 0, 0)
        paint_glass(p, r, 20, hover=h)
        if pr:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, int(30 * pr)))
            p.drawRoundedRect(r, 20, 20)
        badge = QRectF(18, (r.height() - 48) / 2, 48, 48)
        g = QLinearGradient(badge.topLeft(), badge.bottomRight())
        g.setColorAt(0.0, with_alpha(pal.accent_hi, 70 + int(60 * h)))
        g.setColorAt(1.0, with_alpha(pal.accent_lo, 40 + int(50 * h)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(badge, 15, 15)
        paint_icon(p, self._icon, badge.adjusted(12, 12, -12, -12), pal.text, 1.8)
        shift = 2.0 * h
        p.setFont(font(15, "semibold"))
        p.setPen(pal.text)
        p.drawText(
            QRectF(82 + shift, 20, r.width() - 96, 24), Qt.AlignmentFlag.AlignVCenter, self._title
        )
        p.setFont(font(13, "regular"))
        p.setPen(pal.muted)
        p.drawText(
            QRectF(82 + shift, 46, r.width() - 96, 24),
            Qt.AlignmentFlag.AlignVCenter,
            self._subtitle,
        )
        if self.hasFocus():
            p.setPen(QPen(pal.accent_hi, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 20, 20)
