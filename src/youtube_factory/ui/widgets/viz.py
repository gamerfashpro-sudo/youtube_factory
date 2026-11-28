"""Small data widgets: score ring, timeline bar, step list and thumbnail."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from youtube_factory.ui.fonts import font
from youtube_factory.ui.icons import paint_icon
from youtube_factory.ui.motion import Tween, mix, with_alpha
from youtube_factory.ui.theme import theme


class ScoreRing(QWidget):
    """Circular 0-100 score. The arc grows once when the value is first shown."""

    def __init__(self, size: int = 54, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._score = 0
        self._fill = Tween(self)
        self.setFixedSize(size, size)
        self.setFont(font(max(11, size // 3), "semibold"))

    def set_score(self, score: int, animate: bool = False) -> None:
        self._score = max(0, min(100, score))
        if animate:
            self._fill.jump(0.0)
            self._fill.go(1.0, 700)
        else:
            self._fill.jump(1.0)

    def score(self) -> int:
        return self._score

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = 4.0
        r = QRectF(self.rect()).adjusted(w / 2 + 1, w / 2 + 1, -w / 2 - 1, -w / 2 - 1)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(pal.track, w))
        p.drawEllipse(r)
        sweep = -360.0 * (self._score / 100.0) * self._fill.value
        if sweep:
            pen = QPen(pal.amber, w)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(r, 90 * 16, int(sweep * 16))
        p.setPen(pal.text)
        p.setFont(self.font())
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, str(self._score))


class TimelineBar(QWidget):
    """Where the Short sits inside the whole video, with amber trim handles."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start = 0.0
        self._end = 0.0
        self._total = 0.0
        self._grow = Tween(self, value=1.0)
        self.setFixedHeight(18)
        self.setMinimumWidth(80)

    def set_range(self, start: float, end: float, total: float) -> None:
        self._start, self._end = start, end
        self._total = max(total, end, 1.0)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        track = QRectF(0, h / 2 - 3, w, 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.track)
        p.drawRoundedRect(track, 3, 3)
        x1 = w * self._start / self._total
        x2 = max(x1 + 10, w * self._end / self._total)
        x2 = min(x2, w - 0.0)
        seg = QRectF(x1, h / 2 - 3, x2 - x1, 6)
        g = QLinearGradient(seg.topLeft(), seg.topRight())
        g.setColorAt(0.0, pal.amber)
        g.setColorAt(1.0, mix(pal.amber, QColor("#FF7A45"), 0.6))
        p.setBrush(g)
        p.drawRoundedRect(seg, 3, 3)
        # Trim handles
        p.setBrush(pal.amber)
        for x in (x1, x2):
            p.drawRoundedRect(QRectF(x - 2, 1, 4, h - 2), 2, 2)


class Stepper(QWidget):
    """Vertical list of steps: done ticks, a spinner on the current step, dim future steps."""

    ROW = 38

    def __init__(self, steps: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        self._failed = False
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._spin)
        self.setFont(font(15, "medium"))
        self.setFixedHeight(self.ROW * len(steps))
        self.setMinimumWidth(280)

    def set_state(self, current: int, failed: bool = False) -> None:
        self._current, self._failed = current, failed
        self._sync_timer()
        self.update()

    def _sync_timer(self) -> None:
        running = (
            self.isVisible()
            and not self._failed
            and self._current < len(self._steps)
            and theme_motion()
        )
        if running and not self._timer.isActive():
            self._timer.start()
        elif not running and self._timer.isActive():
            self._timer.stop()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().hideEvent(event)
        self._timer.stop()

    def _spin(self) -> None:
        self._angle = (self._angle + 7.0) % 360.0
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(360, self.ROW * len(self._steps))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(self.font())
        for i, text in enumerate(self._steps):
            cy = self.ROW * i + self.ROW / 2
            dot = QRectF(2, cy - 11, 22, 22)
            if i < self._current:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(with_alpha(pal.success, 60))
                p.drawEllipse(dot)
                paint_icon(p, "check", dot.adjusted(4, 4, -4, -4), pal.success, 2.2)
                color = pal.muted
            elif i == self._current:
                if self._failed:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(with_alpha(pal.danger, 60))
                    p.drawEllipse(dot)
                    paint_icon(p, "close", dot.adjusted(5, 5, -5, -5), pal.danger, 2.2)
                    color = pal.danger
                else:
                    ring = dot.adjusted(2, 2, -2, -2)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(with_alpha(pal.accent, 70), 2.4))
                    p.drawEllipse(ring)
                    pen = QPen(pal.accent_hi, 2.4)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    p.setPen(pen)
                    p.drawArc(ring, int(-self._angle * 16), 100 * 16)
                    color = pal.text
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(with_alpha(pal.text, 50), 1.6))
                p.drawEllipse(dot.adjusted(3, 3, -3, -3))
                color = pal.faint
            p.setPen(color)
            p.drawText(
                QRectF(38, cy - 14, self.width() - 40, 28),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )


def theme_motion() -> bool:
    from youtube_factory.ui.motion import motion

    return motion.enabled


class Thumb(QWidget):
    """Rounded video thumbnail; shows a film icon when there is no picture."""

    def __init__(self, width: int = 128, height: int = 72, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pm: QPixmap | None = None
        self.setFixedSize(width, height)

    def set_image(self, data: bytes | None) -> None:
        self._pm = None
        if data:
            img = QImage.fromData(data)
            if not img.isNull():
                self._pm = QPixmap.fromImage(img).scaled(
                    self.size() * self.devicePixelRatioF(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        if self._pm is not None:
            p.setClipPath(path)
            p.drawPixmap(self.rect(), self._pm)
            p.setClipping(False)
        else:
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0.0, with_alpha(pal.accent, 90))
            g.setColorAt(1.0, with_alpha(pal.amber, 50))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawPath(path)
            paint_icon(
                p, "film", QRectF(r.center().x() - 14, r.center().y() - 14, 28, 28), pal.text, 1.7
            )
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(with_alpha(QColor("white"), 40), 1.0))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 13.5, 13.5)


class ProgressLine(QWidget):
    """Slim progress bar that glides to each new value."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = Tween(self)
        self.kind = "work"  # work, done, failed
        self.setFixedHeight(6)

    def set_value(self, fraction: float, animate: bool = True) -> None:
        fraction = max(0.0, min(1.0, fraction))
        if animate:
            self._value.go(fraction, 350)
        else:
            self._value.jump(fraction)

    def value(self) -> float:
        return self._value.value

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        pal = theme.p
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.track)
        p.drawRoundedRect(r, 3, 3)
        width = r.width() * self._value.value
        if width < 1:
            return
        fill = QRectF(0, 0, max(width, 6.0), r.height())
        if self.kind == "failed":
            p.setBrush(pal.danger)
        elif self.kind == "done":
            p.setBrush(pal.success)
        else:
            g = QLinearGradient(fill.topLeft(), fill.topRight())
            g.setColorAt(0.0, pal.accent)
            g.setColorAt(1.0, pal.accent_hi)
            p.setBrush(g)
        p.drawRoundedRect(fill, 3, 3)
