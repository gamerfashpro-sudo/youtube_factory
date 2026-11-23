"""Results screen: video header, toolbar and a responsive grid of Shorts cards."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.models import Analysis, AnalysisMode, Short
from youtube_factory.services import exporter
from youtube_factory.services.analyzer import format_time
from youtube_factory.ui.widgets.common import make_button, make_card, make_label
from youtube_factory.ui.widgets.short_card import ShortCard

CARD_MIN_WIDTH = 380


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", title).strip(" ._")
    return name[:60] or "shorts"


def confirm(parent: QWidget, title: str, text: str) -> bool:
    box = QMessageBox(QMessageBox.Icon.Question, title, text, parent=parent)
    yes = box.addButton(ru.BTN_DELETE, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(ru.BTN_CANCEL, QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is yes


class ResultsView(QWidget):
    new_analysis_requested = Signal()
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._analysis: Analysis | None = None
        self._cards: list[ShortCard] = []
        self._columns = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 20)
        outer.setSpacing(14)

        header = make_card()
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 16, 18, 16)
        self.thumb = make_label("▶")
        self.thumb.setFixedSize(160, 90)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet(
            "background: #1C1C20; border-radius: 10px; color: #7C5CFF; font-size: 28pt;"
        )
        h.addWidget(self.thumb)
        info = QVBoxLayout()
        self.title_label = make_label(wrap=True, h2=True)
        self.meta_label = make_label(wrap=True, muted=True)
        self.url_btn = make_button(ru.BTN_OPEN_VIDEO)
        info.addWidget(self.title_label)
        info.addWidget(self.meta_label)
        row = QHBoxLayout()
        row.addWidget(self.url_btn)
        row.addStretch(1)
        info.addLayout(row)
        h.addLayout(info, 1)
        outer.addWidget(header)

        toolbar = QHBoxLayout()
        self.fav_filter = QCheckBox(ru.BTN_FAVORITES_ONLY)
        self.json_btn = make_button(ru.BTN_EXPORT_JSON, ru.EXPORT_SELECTED_HINT)
        self.csv_btn = make_button(ru.BTN_EXPORT_CSV, ru.EXPORT_SELECTED_HINT)
        self.new_btn = make_button(ru.BTN_NEW_ANALYSIS, primary=True)
        toolbar.addWidget(self.fav_filter)
        toolbar.addStretch(1)
        for b in (self.json_btn, self.csv_btn, self.new_btn):
            toolbar.addWidget(b)
        outer.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid_host)
        outer.addWidget(self.scroll, 1)
        self.empty_label = make_label(ru.RESULTS_EMPTY, wrap=True, muted=True)
        self.empty_label.hide()
        outer.addWidget(self.empty_label)

        self.url_btn.clicked.connect(self._open_url)
        self.fav_filter.toggled.connect(lambda _: self._relayout())
        self.json_btn.clicked.connect(lambda: self._export("json"))
        self.csv_btn.clicked.connect(lambda: self._export("csv"))
        self.new_btn.clicked.connect(self.new_analysis_requested)

    # --- data -------------------------------------------------------------
    def set_analysis(self, analysis: Analysis) -> None:
        self._analysis = analysis
        v = analysis.video
        self.title_label.setText(v.title or ru.DEFAULT_VIDEO_TITLE)
        mode = ru.MODE_DEMO if analysis.mode == AnalysisMode.DEMO else ru.MODE_MANUAL
        parts = [p for p in (v.channel, mode) if p]
        if v.duration_sec:
            parts.append(f"{ru.DURATION_LABEL}: {format_time(v.duration_sec)}")
        self.meta_label.setText(" · ".join(parts))
        self.url_btn.setVisible(bool(v.url))
        self.fav_filter.setChecked(False)
        for card in self._cards:
            card.deleteLater()
        self._cards = []
        for short in analysis.shorts:
            self._cards.append(self._make_card(short))
        self._columns = 0
        self._relayout()

    def _make_card(self, short: Short) -> ShortCard:
        card = ShortCard(short)
        card.copy_requested.connect(self._copy)
        card.save_requested.connect(self._save_text)
        card.favorite_toggled.connect(self._toggle_favorite)
        card.delete_requested.connect(self._delete)
        return card

    # --- layout -----------------------------------------------------------
    def _visible_cards(self) -> list[ShortCard]:
        if self.fav_filter.isChecked():
            return [c for c in self._cards if c.short.is_favorite]
        return list(self._cards)

    def _relayout(self) -> None:
        for card in self._cards:
            self.grid.removeWidget(card)
            card.hide()
        visible = self._visible_cards()
        width = max(self.scroll.viewport().width(), CARD_MIN_WIDTH)
        cols = max(1, width // CARD_MIN_WIDTH)
        self._columns = cols
        for i, card in enumerate(visible):
            self.grid.addWidget(card, i // cols, i % cols)
            card.show()
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)
        self.empty_label.setVisible(not visible)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        cols = max(1, max(self.scroll.viewport().width(), CARD_MIN_WIDTH) // CARD_MIN_WIDTH)
        if cols != self._columns and self._cards:
            self._relayout()

    # --- actions ----------------------------------------------------------
    def _open_url(self) -> None:
        if self._analysis and not QDesktopServices.openUrl(QUrl(self._analysis.video.url)):
            self.toast_requested.emit(ru.ERR_OPEN_URL, True)

    def _copy(self, short: Short) -> None:
        QGuiApplication.clipboard().setText(exporter.short_to_text(short))
        self.toast_requested.emit(ru.TOAST_COPIED, False)

    def _save_text(self, short: Short, hook: str, title: str, description: str) -> None:
        self._controller.save_short_text(short, hook, title, description)
        self.toast_requested.emit(ru.TOAST_SAVED, False)

    def _toggle_favorite(self, short: Short) -> None:
        self._controller.set_favorite(short, not short.is_favorite)
        for card in self._cards:
            if card.short is short:
                card.refresh()
        self.toast_requested.emit(
            ru.TOAST_FAV_ADDED if short.is_favorite else ru.TOAST_FAV_REMOVED, False
        )
        if self.fav_filter.isChecked():
            self._relayout()

    def _delete(self, short: Short) -> None:
        if not confirm(self, ru.CONFIRM_DELETE_TITLE, ru.CONFIRM_DELETE_SHORT):
            return
        self._controller.delete_short(short)
        if self._analysis:
            self._analysis.shorts = [s for s in self._analysis.shorts if s is not short]
        for card in [c for c in self._cards if c.short is short]:
            self.grid.removeWidget(card)
            card.deleteLater()
            self._cards.remove(card)
        self._relayout()
        self.toast_requested.emit(ru.TOAST_DELETED, False)

    def _shorts_to_export(self) -> list[Short]:
        chosen = [c.short for c in self._cards if c.is_selected()]
        return chosen or [c.short for c in self._cards]

    def _export(self, kind: str) -> None:
        if not self._analysis or not self._cards:
            return
        base = Path(self._controller.settings.export_dir or Path.home())
        name = safe_filename(self._analysis.video.title) + f".{kind}"
        title = ru.EXPORT_JSON_TITLE if kind == "json" else ru.EXPORT_CSV_TITLE
        flt = ru.EXPORT_JSON_FILTER if kind == "json" else ru.EXPORT_CSV_FILTER
        path, _ = QFileDialog.getSaveFileName(self, title, str(base / name), flt)
        if not path:
            return
        self.export_to(Path(path), kind)

    def export_to(self, path: Path, kind: str) -> bool:
        """Write the export file; reports success or failure as a toast."""
        if not self._analysis:
            return False
        shorts = self._shorts_to_export()
        try:
            if kind == "json":
                exporter.export_json(path, self._analysis.video, shorts)
            else:
                exporter.export_csv(path, shorts)
        except exporter.ExportError as exc:
            self.toast_requested.emit(ru.ERR_EXPORT.format(reason=exc), True)
            return False
        self.toast_requested.emit(ru.TOAST_EXPORTED.format(path=path.name), False)
        return True
