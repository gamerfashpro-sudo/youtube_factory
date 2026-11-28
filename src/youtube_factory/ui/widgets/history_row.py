"""One row in a list of past analyses (used on Home and History)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.data.repositories import HistoryItem
from youtube_factory.models import AnalysisMode
from youtube_factory.ui.widgets.common import make_label
from youtube_factory.ui.widgets.controls import Chip, GlassButton, icon_button
from youtube_factory.ui.widgets.glass import GlassPanel


class HistoryRow(GlassPanel):
    open_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, item: HistoryItem, deletable: bool, parent: QWidget | None = None):
        super().__init__(parent, radius=18, hoverable=True)
        self.item = item
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 14, 14, 14)
        row.setSpacing(12)
        text = QVBoxLayout()
        text.setSpacing(8)
        text.addWidget(make_label(item.title or ru.DEFAULT_VIDEO_TITLE, wrap=True, role="h3"))
        chips = QHBoxLayout()
        chips.setSpacing(6)
        mode = ru.MODE_DEMO if item.mode == AnalysisMode.DEMO else ru.MODE_MANUAL
        chips.addWidget(Chip(f"{item.created_at:%d.%m.%Y %H:%M}", "meta", "clock"))
        chips.addWidget(Chip(mode, "meta"))
        chips.addWidget(Chip(ru.SHORTS_COUNT.format(n=item.shorts_count), "tag", "film"))
        chips.addStretch(1)
        text.addLayout(chips)
        row.addLayout(text, 1)
        self.open_btn = GlassButton(ru.BTN_OPEN, "secondary", "play")
        self.open_btn.clicked.connect(lambda: self.open_requested.emit(item.id))
        row.addWidget(self.open_btn)
        if deletable:
            self.delete_btn = icon_button("trash", ru.TIP_DELETE, "danger")
            self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(item.id))
            row.addWidget(self.delete_btn)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if self.rect().contains(event.position().toPoint()):
            self.open_requested.emit(self.item.id)
        super().mouseReleaseEvent(event)
