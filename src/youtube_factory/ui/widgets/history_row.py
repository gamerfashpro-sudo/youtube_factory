"""One row in a list of past analyses (used on Home and History)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.data.repositories import HistoryItem
from youtube_factory.models import AnalysisMode
from youtube_factory.ui.widgets.common import make_button, make_card, make_label


class HistoryRow(QWidget):
    open_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, item: HistoryItem, deletable: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = make_card()
        outer.addWidget(card)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        text = QVBoxLayout()
        title = item.title or ru.DEFAULT_VIDEO_TITLE
        text.addWidget(make_label(title, wrap=True))
        mode = ru.MODE_DEMO if item.mode == AnalysisMode.DEMO else ru.MODE_MANUAL
        count = ru.SHORTS_COUNT.format(n=item.shorts_count)
        meta = f"{item.created_at:%d.%m.%Y %H:%M} · {mode} · {count}"
        text.addWidget(make_label(meta, muted=True))
        row.addLayout(text, 1)
        open_btn = make_button(ru.BTN_OPEN)
        open_btn.clicked.connect(lambda: self.open_requested.emit(item.id))
        row.addWidget(open_btn)
        if deletable:
            delete_btn = make_button(ru.BTN_DELETE, ru.TIP_DELETE, danger=True)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(item.id))
            row.addWidget(delete_btn)
