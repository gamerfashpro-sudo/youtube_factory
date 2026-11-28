"""Cheap animation helpers.

Every animation is event driven (hover, click, page change) and repaints only the
widget that owns it. Nothing runs while the interface is idle. Animations can be
switched off globally, then every tween jumps straight to its target value.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget


class _Motion:
    enabled = True


motion = _Motion()


def mix(a: QColor, b: QColor, t: float) -> QColor:
    """Linear blend of two colours including alpha. t=0 gives a, t=1 gives b."""
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def with_alpha(c: QColor, alpha: int) -> QColor:
    out = QColor(c)
    out.setAlpha(max(0, min(255, int(alpha))))
    return out


class Tween:
    """A float value that glides to a target; repaints its owner on every step."""

    def __init__(
        self,
        owner: QWidget,
        value: float = 0.0,
        curve: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.owner = owner
        self.value = value
        self._on_change = on_change or owner.update
        self._anim = QVariantAnimation(owner)
        self._anim.setEasingCurve(curve)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, v: object) -> None:
        self.value = float(v)
        self._on_change()

    @property
    def running(self) -> bool:
        return self._anim.state() == QVariantAnimation.State.Running

    def go(self, target: float, ms: int = 160) -> None:
        self._anim.stop()
        if not motion.enabled or ms <= 0 or not self.owner.isVisible():
            self.jump(target)
            return
        self._anim.setDuration(ms)
        self._anim.setStartValue(float(self.value))
        self._anim.setEndValue(float(target))
        self._anim.start()

    def jump(self, value: float) -> None:
        self._anim.stop()
        self.value = float(value)
        self._on_change()
