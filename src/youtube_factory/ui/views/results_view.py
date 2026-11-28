"""Results screen: video header, toolbar and a responsive grid of Shorts cards."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.models import Analysis, AnalysisMode, Short
from youtube_factory.services import exporter
from youtube_factory.services.analyzer import format_time
from youtube_factory.services.exporter import safe_filename
from youtube_factory.ui.widgets.common import make_label, transparent_scroll
from youtube_factory.ui.widgets.controls import Chip, GlassButton, Segmented
from youtube_factory.ui.widgets.dialogs import confirm
from youtube_factory.ui.widgets.glass import GlassPanel
from youtube_factory.ui.widgets.short_card import ShortCard
from youtube_factory.ui.widgets.viz import Thumb

CARD_MIN_WIDTH = 440
REVEAL_STEP_MS = 55
REVEAL_MAX = 8  # cards beyond this appear together with the last staggered one

__all__ = ["ResultsView", "confirm"]


class ResultsView(QWidget):
    new_analysis_requested = Signal()
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._analysis: Analysis | None = None
        self._cards: list[ShortCard] = []
        self._columns = 0
        self._fitting = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 20)
        outer.setSpacing(14)

        header = GlassPanel(radius=22, strength=1.1)
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 16, 20, 16)
        h.setSpacing(18)
        self.thumb = Thumb(144, 81)
        h.addWidget(self.thumb)
        info = QVBoxLayout()
        info.setSpacing(8)
        self.title_label = make_label(wrap=True, role="h2")
        info.addWidget(self.title_label)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        info.addLayout(self.chips)
        row = QHBoxLayout()
        self.url_btn = GlassButton(ru.BTN_OPEN_VIDEO, "ghost", "external", height=34)
        row.addWidget(self.url_btn)
        row.addStretch(1)
        info.addLayout(row)
        h.addLayout(info, 1)
        outer.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.fav_filter = Segmented()
        self.fav_filter.addItem(ru.FILTER_ALL, "all")
        self.fav_filter.addItem(ru.FILTER_FAVORITES, "fav")
        self.json_btn = GlassButton(
            ru.BTN_EXPORT_JSON, "secondary", "export", ru.EXPORT_SELECTED_HINT
        )
        self.csv_btn = GlassButton(
            ru.BTN_EXPORT_CSV, "secondary", "export", ru.EXPORT_SELECTED_HINT
        )
        self.new_btn = GlassButton(ru.BTN_NEW_ANALYSIS, "primary", "plus")
        toolbar.addWidget(self.fav_filter)
        toolbar.addStretch(1)
        for b in (self.json_btn, self.csv_btn, self.new_btn):
            toolbar.addWidget(b)
        outer.addLayout(toolbar)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 8)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll = transparent_scroll(self.grid_host)
        self.scroll.viewport().installEventFilter(self)
        outer.addWidget(self.scroll, 1)
        self.empty_label = make_label(ru.RESULTS_EMPTY, wrap=True, role="muted")
        self.empty_label.hide()
        outer.addWidget(self.empty_label)

        self.url_btn.clicked.connect(self._open_url)
        self.fav_filter.currentChanged.connect(lambda _: self._relayout())
        self.json_btn.clicked.connect(lambda: self._export("json"))
        self.csv_btn.clicked.connect(lambda: self._export("csv"))
        self.new_btn.clicked.connect(self.new_analysis_requested)

    # --- data -------------------------------------------------------------
    def set_analysis(self, analysis: Analysis) -> None:
        self._analysis = analysis
        v = analysis.video
        self.title_label.setText(v.title or ru.DEFAULT_VIDEO_TITLE)
        self.thumb.set_image(v.thumbnail)
        while self.chips.count():
            item = self.chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        mode = ru.MODE_DEMO if analysis.mode == AnalysisMode.DEMO else ru.MODE_MANUAL
        if v.channel:
            self.chips.addWidget(Chip(v.channel, "meta", "user"))
        self.chips.addWidget(Chip(mode, "tag"))
        if v.duration_sec:
            self.chips.addWidget(
                Chip(f"{ru.DURATION_LABEL}: {format_time(v.duration_sec)}", "meta", "clock")
            )
        self.chips.addStretch(1)
        self.url_btn.setVisible(bool(v.url))
        self.fav_filter.set_index_silently(0)
        for card in self._cards:
            card.deleteLater()
        self._cards = []
        for short in analysis.shorts:
            self._cards.append(self._make_card(short, v.duration_sec))
        self._columns = 0
        self._relayout()
        for i, card in enumerate(c for c in self._cards if not c.isHidden()):
            card.score_ring.set_score(card.short.score, animate=True)
            card.reveal(min(i, REVEAL_MAX) * REVEAL_STEP_MS)

    def _make_card(self, short: Short, total_sec: float) -> ShortCard:
        card = ShortCard(short, total_sec)
        card.copy_requested.connect(self._copy)
        card.save_requested.connect(self._save_text)
        card.favorite_toggled.connect(self._toggle_favorite)
        card.delete_requested.connect(self._delete)
        return card

    # --- layout -----------------------------------------------------------
    def _favorites_only(self) -> bool:
        return self.fav_filter.currentData() == "fav"

    def _visible_cards(self) -> list[ShortCard]:
        if self._favorites_only():
            return [c for c in self._cards if c.short.is_favorite]
        return list(self._cards)

    def _relayout(self) -> None:
        for card in self._cards:
            self.grid.removeWidget(card)
            card.hide()
        visible = self._visible_cards()
        cols = self._column_count()
        self._columns = cols
        for i, card in enumerate(visible):
            self.grid.addWidget(card, i // cols, i % cols)
            card.show()
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)
        self.empty_label.setVisible(not visible)
        self._fit_heights()

    def _fit_heights(self) -> None:
        """Give every card the height its wrapped text needs.

        QGridLayout underestimates the height of word-wrapped labels, which made
        neighbouring text overlap. Measure after layout and enforce a minimum.
        """
        if self._fitting:
            return
        self._fitting = True
        try:
            visible = [c for c in self._cards if not c.isHidden()]
            for card in visible:
                card.setMinimumHeight(0)
            self.grid.activate()
            for card in visible:
                card.setMinimumHeight(card.layout().heightForWidth(card.width()))
        finally:
            self._fitting = False

    def _column_count(self) -> int:
        return max(1, max(self.scroll.viewport().width(), CARD_MIN_WIDTH) // CARD_MIN_WIDTH)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt override
        # React to the scroll area's real size, which is only known after layout.
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize and self._cards:
            if self._column_count() != self._columns:
                self._relayout()
            else:
                self._fit_heights()
        return super().eventFilter(watched, event)

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
                card.refresh(animate_fav=True)
        self.toast_requested.emit(
            ru.TOAST_FAV_ADDED if short.is_favorite else ru.TOAST_FAV_REMOVED, False
        )
        if self._favorites_only():
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
