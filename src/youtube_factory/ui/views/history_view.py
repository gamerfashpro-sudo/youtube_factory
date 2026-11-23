"""History screen: previous analyses with open and delete (with confirmation)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.ui.views.results_view import confirm
from youtube_factory.ui.widgets.common import make_label
from youtube_factory.ui.widgets.history_row import HistoryRow


class HistoryView(QWidget):
    open_analysis = Signal(int)
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 24)
        outer.setSpacing(14)
        outer.addWidget(make_label(ru.HISTORY_TITLE, h1=True))
        self.empty_label = make_label(ru.HISTORY_EMPTY, muted=True)
        outer.addWidget(self.empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        host = QWidget()
        self.rows = QVBoxLayout(host)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(8)
        self.rows.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        controller.history_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        while self.rows.count() > 1:
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items = self._controller.history()
        self.empty_label.setVisible(not items)
        for i, item in enumerate(items):
            row = HistoryRow(item, deletable=True)
            row.open_requested.connect(self.open_analysis)
            row.delete_requested.connect(self._delete)
            self.rows.insertWidget(i, row)

    def _delete(self, analysis_id: int) -> None:
        item = next((i for i in self._controller.history() if i.id == analysis_id), None)
        title = (item.title if item else "") or ru.DEFAULT_VIDEO_TITLE
        if not confirm(
            self, ru.CONFIRM_DELETE_TITLE, ru.CONFIRM_DELETE_ANALYSIS.format(title=title)
        ):
            return
        self._controller.delete_analysis(analysis_id)
        self.toast_requested.emit(ru.TOAST_CLEAR_HISTORY, False)
