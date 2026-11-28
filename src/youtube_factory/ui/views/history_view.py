"""History screen: previous analyses with open and delete (with confirmation)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.ui.widgets.common import make_label, transparent_scroll
from youtube_factory.ui.widgets.dialogs import confirm
from youtube_factory.ui.widgets.history_row import HistoryRow


class HistoryView(QWidget):
    open_analysis = Signal(int)
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        host = QWidget()
        outer = QVBoxLayout(host)
        outer.setContentsMargins(36, 40, 36, 28)
        outer.setSpacing(0)
        outer.addWidget(make_label(ru.HISTORY_TITLE, role="title"))
        outer.addSpacing(18)
        self.empty_label = make_label(ru.HISTORY_EMPTY, role="muted")
        outer.addWidget(self.empty_label)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(10)
        outer.addLayout(self.rows)
        outer.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(transparent_scroll(host))

        controller.history_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items = self._controller.history()
        self.empty_label.setVisible(not items)
        for item in items:
            row = HistoryRow(item, deletable=True)
            row.open_requested.connect(self.open_analysis)
            row.delete_requested.connect(self._delete)
            self.rows.addWidget(row)

    def _delete(self, analysis_id: int) -> None:
        item = next((i for i in self._controller.history() if i.id == analysis_id), None)
        title = (item.title if item else "") or ru.DEFAULT_VIDEO_TITLE
        if not confirm(
            self, ru.CONFIRM_DELETE_TITLE, ru.CONFIRM_DELETE_ANALYSIS.format(title=title)
        ):
            return
        self._controller.delete_analysis(analysis_id)
        self.toast_requested.emit(ru.TOAST_CLEAR_HISTORY, False)
