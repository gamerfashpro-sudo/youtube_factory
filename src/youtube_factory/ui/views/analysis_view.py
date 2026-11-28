"""Analysis screen: step list with a live spinner, cancel and clear error messages."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.ui.widgets.common import make_label
from youtube_factory.ui.widgets.controls import GlassButton
from youtube_factory.ui.widgets.glass import GlassPanel
from youtube_factory.ui.widgets.viz import Stepper


class AnalysisView(QWidget):
    cancel_requested = Signal()
    back_requested = Signal()
    paste_transcript_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current = 0
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 36, 36, 36)
        outer.addStretch(1)

        panel = GlassPanel(radius=26, strength=1.1)
        panel.setFixedWidth(520)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(34, 30, 34, 28)
        lay.setSpacing(14)
        lay.addWidget(make_label(ru.ANALYSIS_TITLE, role="title"))
        lay.addSpacing(6)
        self.stepper = Stepper(list(ru.STEPS))
        lay.addWidget(self.stepper)

        self.error_label = make_label(wrap=True, role="error")
        self.error_label.hide()
        lay.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.cancel_btn = GlassButton(ru.BTN_CANCEL_ANALYSIS, "secondary", "close")
        self.back_btn = GlassButton(ru.BTN_BACK, "secondary", "back")
        self.paste_btn = GlassButton(ru.BTN_PASTE_TRANSCRIPT, "primary", "paste")
        for b in (self.cancel_btn, self.back_btn, self.paste_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(buttons)

        centre = QHBoxLayout()
        centre.addStretch(1)
        centre.addWidget(panel)
        centre.addStretch(1)
        outer.addLayout(centre)
        outer.addStretch(2)

        self.cancel_btn.clicked.connect(self.cancel_requested)
        self.back_btn.clicked.connect(self.back_requested)
        self.paste_btn.clicked.connect(self.paste_transcript_requested)
        self.reset()

    def reset(self) -> None:
        self.error_label.hide()
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)
        self.back_btn.hide()
        self.paste_btn.hide()
        self.set_step(0)

    def set_step(self, current: int) -> None:
        self._current = current
        self.stepper.set_state(current)

    def _fail(self, message: str, role: str) -> None:
        self.error_label.setProperty("role", role)
        self.error_label.style().unpolish(self.error_label)
        self.error_label.style().polish(self.error_label)
        self.error_label.setText(message)
        self.error_label.show()
        self.cancel_btn.hide()
        self.back_btn.show()
        self.stepper.set_state(self._current, failed=True)

    def show_error(self, message: str, offer_paste: bool) -> None:
        self._fail(message, "error")
        self.paste_btn.setVisible(offer_paste)

    def show_cancelled(self) -> None:
        self._fail(ru.ANALYSIS_CANCELLED, "muted")
        self.paste_btn.hide()
