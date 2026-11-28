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
from youtube_factory.ui.widgets.empty_state import EmptyState
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
        self._batch_total = 0
        self._batch_done = 0
        self._clips_folder = ""

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
        self.clips_btn = GlassButton(ru.BTN_MAKE_ALL, "primary", "film")
        self.new_btn = GlassButton(ru.BTN_NEW_ANALYSIS, "secondary", "plus")
        toolbar.addWidget(self.fav_filter)
        toolbar.addStretch(1)
        for b in (self.json_btn, self.csv_btn, self.new_btn, self.clips_btn):
            toolbar.addWidget(b)
        outer.addLayout(toolbar)

        # One line of status for the whole download batch.
        self.status_row = QWidget()
        status = QHBoxLayout(self.status_row)
        status.setContentsMargins(4, 0, 0, 0)
        self.status_label = make_label(role="muted")
        self.folder_btn = GlassButton(ru.BTN_OPEN_CLIPS, "ghost", "folder", height=32)
        status.addWidget(self.status_label, 1)
        status.addWidget(self.folder_btn)
        self.status_row.hide()
        outer.addWidget(self.status_row)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 8)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll = transparent_scroll(self.grid_host)
        self.scroll.viewport().installEventFilter(self)
        outer.addWidget(self.scroll, 1)
        self.empty_state = EmptyState(
            "star",
            ru.EMPTY_FAVORITES_TITLE,
            ru.EMPTY_FAVORITES_HINT,
            ru.BTN_SHOW_ALL,
            action_variant="secondary",
        )
        self.empty_state.action_clicked.connect(lambda: self.fav_filter.setCurrentIndex(0))
        self.empty_state.hide()
        outer.addWidget(self.empty_state)

        self.url_btn.clicked.connect(self._open_url)
        self.fav_filter.currentChanged.connect(lambda _: self._relayout())
        self.json_btn.clicked.connect(lambda: self._export("json"))
        self.csv_btn.clicked.connect(lambda: self._export("csv"))
        self.new_btn.clicked.connect(self.new_analysis_requested)
        self.clips_btn.clicked.connect(self._clips_button_clicked)
        self.folder_btn.clicked.connect(self._open_clips_folder)
        c = controller
        c.clips_preparing.connect(self._on_preparing)
        c.clip_started.connect(self._on_clip_started)
        c.clip_progress.connect(self._on_clip_progress)
        c.clip_done.connect(self._on_clip_done)
        c.clip_failed.connect(self._on_clip_failed)
        c.clips_finished.connect(self._on_clips_finished)

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
        self.status_row.hide()
        self._update_clips_button()
        for i, card in enumerate(c for c in self._cards if not c.isHidden()):
            card.score_ring.set_score(card.short.score, animate=True)
            card.reveal(min(i, REVEAL_MAX) * REVEAL_STEP_MS)

    def _make_card(self, short: Short, total_sec: float) -> ShortCard:
        card = ShortCard(short, total_sec)
        card.copy_requested.connect(self._copy)
        card.save_requested.connect(self._save_text)
        card.favorite_toggled.connect(self._toggle_favorite)
        card.delete_requested.connect(self._delete)
        card.selection_changed.connect(self._update_clips_button)
        card.make_clip_requested.connect(lambda sh: self._start_clips([sh]))
        card.open_folder_requested.connect(self._open_clips_folder)
        card.clip_btn.setEnabled(self._can_clip())
        card.clip_btn.setToolTip(ru.TIP_MAKE_CLIP if self._can_clip() else ru.CLIPS_NEED_URL)
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
        self._show_empty_state(not visible)
        self._fit_heights()

    def _show_empty_state(self, empty: bool) -> None:
        """Say why the list is empty: no favourites yet, or no Shorts at all."""
        favourites = self._favorites_only()
        if favourites:
            self.empty_state.set_texts(ru.EMPTY_FAVORITES_TITLE, ru.EMPTY_FAVORITES_HINT)
        else:
            self.empty_state.set_texts(ru.EMPTY_RESULTS_TITLE, ru.EMPTY_RESULTS_HINT)
        if self.empty_state.action_btn is not None:
            self.empty_state.action_btn.setVisible(favourites)
        self.empty_state.setVisible(empty)

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

    # --- clips --------------------------------------------------------------
    def _can_clip(self) -> bool:
        return bool(
            self._analysis
            and self._controller.can_make_clips(self._analysis.video, self._analysis.mode)
        )

    def _card_for(self, short: Short) -> ShortCard | None:
        return next((c for c in self._cards if c.short is short), None)

    def _update_clips_button(self) -> None:
        running = self._controller.clips_running
        picked = any(c.is_selected() for c in self._cards)
        if running:
            self.clips_btn.setText(ru.BTN_CANCEL_CLIPS)
            self.clips_btn.variant = "secondary"
            self.clips_btn.set_icon_name("close")
            self.clips_btn.setEnabled(True)
        else:
            self.clips_btn.setText(ru.BTN_MAKE_SELECTED if picked else ru.BTN_MAKE_ALL)
            self.clips_btn.variant = "primary"
            self.clips_btn.set_icon_name("film")
            can = self._can_clip() and bool(self._cards)
            self.clips_btn.setEnabled(can)
            self.clips_btn.setToolTip("" if can or not self._cards else ru.CLIPS_NEED_URL)
        for card in self._cards:
            if card.clip_state not in ("queued", "working"):
                card.clip_btn.setEnabled(not running and self._can_clip())
        self.clips_btn.updateGeometry()
        self.clips_btn.update()

    def _clips_button_clicked(self) -> None:
        if self._controller.clips_running:
            self._controller.cancel_clips()
            return
        chosen = [c.short for c in self._cards if c.is_selected()]
        self._start_clips(chosen or [c.short for c in self._visible_cards()])

    def _start_clips(self, shorts: list[Short]) -> None:
        if not self._analysis or not shorts:
            return
        if self._controller.clips_running:
            return
        if not self._controller.start_clips(self._analysis.video, shorts, self._analysis.mode):
            self.toast_requested.emit(ru.CLIPS_NEED_URL, True)
            return
        self._batch_total = len(shorts)
        self._batch_done = 0
        for short in shorts:
            card = self._card_for(short)
            if card:
                card.set_clip_state("queued", ru.CLIP_WAITING)
        self._set_status(ru.CLIP_WAITING)
        self.folder_btn.hide()
        self._update_clips_button()
        self._fit_heights()

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_row.show()

    def _on_preparing(self, tool: str, fraction: float) -> None:
        self._set_status(ru.CLIP_TOOLS_PREPARING.format(tool=tool, percent=int(fraction * 100)))

    def _on_clip_started(self, short: Short) -> None:
        card = self._card_for(short)
        if card:
            card.set_clip_state("working", ru.CLIP_WORKING.format(percent=0), 0.0)
            self._fit_heights()
        self._set_status(ru.CLIPS_PROGRESS.format(n=self._batch_done + 1, total=self._batch_total))

    def _on_clip_progress(self, short: Short, fraction: float) -> None:
        card = self._card_for(short)
        if card:
            card.set_clip_state(
                "working", ru.CLIP_WORKING.format(percent=int(fraction * 100)), fraction
            )

    def _on_clip_done(self, short: Short, path: str) -> None:
        self._batch_done += 1
        card = self._card_for(short)
        if card:
            card.set_clip_state("done", ru.CLIP_READY.format(name=Path(path).name), 1.0)

    def _on_clip_failed(self, short: Short, reason: str) -> None:
        self._batch_done += 1
        card = self._card_for(short)
        if card:
            card.set_clip_state("failed", ru.CLIP_FAILED.format(reason=reason), 1.0)
            self._fit_heights()

    def _on_clips_finished(self, ok: int, failed: int, cancelled: bool, folder: str) -> None:
        total = getattr(self, "_batch_total", ok + failed)
        for card in self._cards:
            if card.clip_state in ("queued", "working"):
                card.set_clip_state("idle")
        self._clips_folder = folder
        if cancelled:
            message = ru.CLIPS_BATCH_CANCELLED.format(ok=ok)
        elif failed:
            message = ru.CLIPS_BATCH_PARTIAL.format(ok=ok, total=total, failed=failed)
        else:
            message = ru.CLIPS_BATCH_DONE.format(ok=ok, total=total, folder=Path(folder).name)
        self._set_status(message)
        self.folder_btn.setVisible(ok > 0)
        self.toast_requested.emit(message, bool(failed) and not ok)
        self._update_clips_button()
        self._fit_heights()

    def _open_clips_folder(self) -> None:
        folder = getattr(self, "_clips_folder", "") or self._controller.clips_folder()
        Path(folder).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

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
