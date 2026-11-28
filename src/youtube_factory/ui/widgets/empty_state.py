"""Empty screens: a glowing glass tile, a short title, one line of help, one action.

The tile pops in once when the screen is shown. Nothing loops, so an empty screen costs
no CPU while the person reads it.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, with_alpha
from youtube_factory.ui.theme import theme
from youtube_factory.ui.widgets.common import make_label
from youtube_factory.ui.widgets.controls import GlassButton
from youtube_factory.ui.widgets.glass import paint_glass
from youtube_factory.ui.widgets.glow import paint_glow


class EmptyArt(QWidget):
    """The picture: two faint rings, a glowing glass tile and an icon on it."""

    def __init__(self, icon: str, compact: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._tile = 56.0 if compact else 76.0
        self._appear = Tween(self, value=1.0, curve=QEasingCurve.Type.OutBack)
        self.setFixedSize(QSize(230, int(self._tile + 70)))

    def play(self) -> None:
        """Pop in (or just show, when animations are off)."""
        self._appear.jump(0.0)
        self._appear.go(1.0, 520)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.play()
        super().showEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        t = self._appear.value
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(self.width() / 2, self.height() / 2)
        scale = 0.84 + 0.16 * t
        p.scale(scale, scale)
        p.setOpacity(max(0.0, min(1.0, t * 1.5)))

        s = self._tile
        for i, extra in enumerate((34.0, 68.0)):  # quiet rings give the tile some depth
            half = (s + extra) / 2
            ring = QRectF(-half, -half, 2 * half, 2 * half)
            p.setPen(QPen(with_alpha(pal.text, (16, 8)[i] if pal.dark else (24, 12)[i]), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(ring, s * 0.3 + extra / 2, s * 0.3 + extra / 2)

        tile = QRectF(-s / 2, -s / 2, s, s)
        paint_glow(p, tile, s * 0.3, pal.accent_hi, 20, 78 if pal.dark else 52)
        paint_glass(p, tile, s * 0.3, strength=1.6, tint=with_alpha(pal.accent, 52))
        size = s * 0.42
        paint_icon(p, self._icon, QRectF(-size / 2, -size / 2, size, size), pal.accent_hi, 1.8)
        p.end()


class EmptyState(QWidget):
    action_clicked = Signal()

    def __init__(
        self,
        icon: str,
        title: str,
        hint: str,
        action_text: str = "",
        action_icon: str | None = None,
        action_variant: str = "primary",
        compact: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8 if compact else 28, 0, 8 if compact else 28)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.art = EmptyArt(icon, compact)
        lay.addWidget(self.art, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(4 if compact else 10)
        self.title_label = make_label(title, role="h2")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.hint_label = make_label(hint, wrap=True, role="muted")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setMinimumWidth(330)
        self.hint_label.setMaximumWidth(400)
        lay.addWidget(self.hint_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.action_btn: GlassButton | None = None
        if action_text:
            lay.addSpacing(10)
            self.action_btn = GlassButton(action_text, action_variant, action_icon, height=42)
            self.action_btn.clicked.connect(self.action_clicked)
            lay.addWidget(self.action_btn, 0, Qt.AlignmentFlag.AlignHCenter)

    def set_texts(self, title: str, hint: str) -> None:
        self.title_label.setText(title)
        self.hint_label.setText(hint)
