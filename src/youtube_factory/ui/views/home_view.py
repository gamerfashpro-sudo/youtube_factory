"""Home screen: URL input, primary actions and recent analyses."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.ui.widgets.common import make_button, make_label
from youtube_factory.ui.widgets.history_row import HistoryRow


class HomeView(QWidget):
    open_analysis = Signal(int)
    paste_transcript_requested = Signal(str)  # current URL text (may be empty)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 32)
        outer.setSpacing(14)

        outer.addWidget(make_label(ru.APP_NAME_RU, h1=True))
        outer.addWidget(make_label(ru.HOME_TAGLINE, h2=True))
        outer.addWidget(make_label(ru.HOME_SUBTITLE, wrap=True, muted=True))
        outer.addSpacing(10)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(ru.URL_PLACEHOLDER)
        self.url_edit.setProperty("big", True)
        self.url_edit.setClearButtonEnabled(True)
        outer.addWidget(self.url_edit)
        self.error_label = make_label(wrap=True, error=True)
        self.error_label.hide()
        outer.addWidget(self.error_label)

        buttons = QHBoxLayout()
        self.create_btn = make_button(ru.BTN_CREATE, primary=True)
        self.example_btn = make_button(ru.BTN_EXAMPLE)
        self.paste_btn = make_button(ru.BTN_PASTE_TRANSCRIPT)
        for b in (self.create_btn, self.example_btn, self.paste_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        outer.addLayout(buttons)
        outer.addSpacing(18)

        outer.addWidget(make_label(ru.RECENT_TITLE, h2=True))
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(8)
        outer.addLayout(self.recent_box)
        outer.addStretch(1)

        self.create_btn.clicked.connect(self._create)
        self.url_edit.returnPressed.connect(self._create)
        self.example_btn.clicked.connect(self._example)
        self.paste_btn.clicked.connect(lambda: self.paste_transcript_requested.emit(self._url()))
        self.url_edit.textChanged.connect(lambda _: self.error_label.hide())
        controller.history_changed.connect(self.refresh_recent)
        self.refresh_recent()

    def _url(self) -> str:
        return self.url_edit.text().strip()

    def show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.show()

    def _create(self) -> None:
        error = self._controller.validate_url(self._url())
        if error:
            self.show_error(error)
            return
        self._controller.start_url(self._url())

    def _example(self) -> None:
        self.error_label.hide()
        self._controller.start_demo()

    def refresh_recent(self) -> None:
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items = self._controller.history(limit=5)
        if not items:
            empty = make_label(ru.RECENT_EMPTY, wrap=True, muted=True)
            empty.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.recent_box.addWidget(empty)
            return
        for item in items:
            row = HistoryRow(item, deletable=False)
            row.open_requested.connect(self.open_analysis)
            self.recent_box.addWidget(row)
