"""Analysis screen: five-step progress, cancel and clear error messages."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.ui.widgets.common import make_button, make_card, make_label, set_prop


class AnalysisView(QWidget):
    cancel_requested = Signal()
    back_requested = Signal()
    paste_transcript_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 32)
        outer.setSpacing(16)
        outer.addWidget(make_label(ru.ANALYSIS_TITLE, h1=True))

        card = make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        self._step_labels = [make_label() for _ in ru.STEPS]
        for label in self._step_labels:
            card_layout.addWidget(label)
        self.bar = QProgressBar()
        self.bar.setRange(0, len(ru.STEPS))
        self.bar.setTextVisible(False)
        card_layout.addWidget(self.bar)
        outer.addWidget(card)

        self.error_label = make_label(wrap=True, error=True)
        self.error_label.hide()
        outer.addWidget(self.error_label)

        buttons = QHBoxLayout()
        self.cancel_btn = make_button(ru.BTN_CANCEL_ANALYSIS)
        self.back_btn = make_button(ru.BTN_BACK)
        self.paste_btn = make_button(ru.BTN_PASTE_TRANSCRIPT, primary=True)
        for b in (self.cancel_btn, self.paste_btn, self.back_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        outer.addLayout(buttons)
        outer.addStretch(1)

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
        for i, label in enumerate(self._step_labels):
            if i < current:
                mark, muted = "✓", True
            elif i == current:
                mark, muted = "●", False
            else:
                mark, muted = "○", True
            label.setText(f"{mark}  {ru.STEPS[i]}")
            label.setProperty("muted", muted)
            label.style().unpolish(label)
            label.style().polish(label)
        self.bar.setValue(current)

    def show_error(self, message: str, offer_paste: bool) -> None:
        set_prop(self.error_label, "error", True)
        set_prop(self.error_label, "muted", False)
        self.error_label.setText(message)
        self.error_label.show()
        self.cancel_btn.hide()
        self.back_btn.show()
        self.paste_btn.setVisible(offer_paste)

    def show_cancelled(self) -> None:
        self.show_error(ru.ANALYSIS_CANCELLED, offer_paste=False)
        set_prop(self.error_label, "error", False)
        set_prop(self.error_label, "muted", True)
