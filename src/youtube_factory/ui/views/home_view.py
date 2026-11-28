"""Home screen: URL input, two quick actions and recent analyses."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.ui.widgets.common import make_label, transparent_scroll
from youtube_factory.ui.widgets.controls import ActionTile, GlassButton
from youtube_factory.ui.widgets.empty_state import EmptyState
from youtube_factory.ui.widgets.fields import GlassLineEdit
from youtube_factory.ui.widgets.glass import GlassPanel
from youtube_factory.ui.widgets.history_row import HistoryRow

CONTENT_MAX = 860


class HomeView(QWidget):
    open_analysis = Signal(int)
    paste_transcript_requested = Signal(str)  # current URL text (may be empty)
    history_requested = Signal()

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        host = QWidget()
        page = QHBoxLayout(host)
        page.setContentsMargins(36, 40, 36, 32)
        column = QWidget()
        column.setMaximumWidth(CONTENT_MAX)
        page.addWidget(column, 1)
        page.addStretch(0)
        outer = QVBoxLayout(column)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(make_label(ru.APP_NAME_RU, role="hero"))
        outer.addSpacing(8)
        outer.addWidget(make_label(ru.HOME_TAGLINE, wrap=True, role="h2"))
        outer.addSpacing(6)
        outer.addWidget(make_label(ru.HOME_SUBTITLE, wrap=True, role="muted"))
        outer.addSpacing(26)

        # The input "lens": a large glass bar with the main action inside it.
        lens = GlassPanel(radius=24, strength=1.2)
        lens_row = QHBoxLayout(lens)
        lens_row.setContentsMargins(10, 10, 10, 10)
        lens_row.setSpacing(8)
        self.url_edit = GlassLineEdit(ru.URL_PLACEHOLDER, "link", height=48)
        self.url_edit.setClearButtonEnabled(True)
        self.create_btn = GlassButton(ru.BTN_CREATE, "primary", "sparkle", height=48)
        lens_row.addWidget(self.url_edit, 1)
        lens_row.addWidget(self.create_btn)
        outer.addWidget(lens)
        outer.addSpacing(8)
        self.error_label = make_label(wrap=True, role="error")
        self.error_label.hide()
        outer.addWidget(self.error_label)
        outer.addSpacing(14)

        tiles = QHBoxLayout()
        tiles.setSpacing(14)
        self.example_btn = ActionTile(ru.TILE_DEMO_TITLE, ru.TILE_DEMO_TEXT, "play")
        self.paste_btn = ActionTile(ru.TILE_PASTE_TITLE, ru.TILE_PASTE_TEXT, "paste")
        tiles.addWidget(self.example_btn, 1)
        tiles.addWidget(self.paste_btn, 1)
        outer.addLayout(tiles)
        outer.addSpacing(34)

        head = QHBoxLayout()
        head.addWidget(make_label(ru.RECENT_TITLE, role="h2"))
        head.addStretch(1)
        self.all_btn = GlassButton(ru.BTN_ALL_HISTORY, "ghost", "clock", height=36)
        head.addWidget(self.all_btn)
        outer.addLayout(head)
        outer.addSpacing(10)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(10)
        outer.addLayout(self.recent_box)
        outer.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(transparent_scroll(host))

        self.create_btn.clicked.connect(self._create)
        self.url_edit.returnPressed.connect(self._create)
        self.example_btn.clicked.connect(self._example)
        self.paste_btn.clicked.connect(lambda: self.paste_transcript_requested.emit(self._url()))
        self.all_btn.clicked.connect(self.history_requested)
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
        items = self._controller.history(limit=3)
        self.all_btn.setVisible(bool(items))
        if not items:
            self.recent_box.addWidget(
                EmptyState("clock", ru.EMPTY_RECENT_TITLE, ru.EMPTY_RECENT_HINT, compact=True)
            )
            return
        for item in items:
            row = HistoryRow(item, deletable=False)
            row.open_requested.connect(self.open_analysis)
            self.recent_box.addWidget(row)
