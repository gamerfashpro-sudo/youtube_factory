"""Application controller: connects the UI to services, workers and storage."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from youtube_factory.app.workers import (
    MANUAL_FALLBACK_CODES,
    AnalysisRequest,
    AnalysisWorker,
    error_code,
    error_message,
)
from youtube_factory.data.repositories import AnalysisRepository, HistoryItem
from youtube_factory.data.settings_store import Settings, SettingsStore
from youtube_factory.integrations.base import VideoSource
from youtube_factory.models import Analysis, AnalysisMode, Short, TranscriptSegment
from youtube_factory.services.url_parser import InvalidUrlError, extract_video_id

log = logging.getLogger(__name__)


class AppController(QObject):
    analysis_started = Signal()
    analysis_progress = Signal(int)
    analysis_finished = Signal(object)
    analysis_failed = Signal(str, bool)  # message, can offer manual transcript
    analysis_cancelled = Signal()
    history_changed = Signal()
    settings_changed = Signal(object)

    def __init__(
        self,
        repo: AnalysisRepository,
        settings_store: SettingsStore,
        parent: QObject | None = None,
        source: VideoSource | None = None,
    ) -> None:
        super().__init__(parent)
        self.source = source
        self.repo = repo
        self._settings_store = settings_store
        self.settings: Settings = settings_store.load()
        self._worker: AnalysisWorker | None = None
        self.last_url = ""
        self.last_title = ""

    # --- analysis ---------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def validate_url(self, text: str) -> str | None:
        """Return an error message for a bad URL, or None if it is valid."""
        if not text.strip():
            return error_message("empty_url")
        try:
            extract_video_id(text)
        except InvalidUrlError as exc:
            return error_message(error_code(exc))
        return None

    def start_demo(self) -> None:
        self._start(AnalysisRequest(AnalysisMode.DEMO))

    def start_url(self, url: str) -> None:
        self.last_url, self.last_title = url, ""
        self._start(AnalysisRequest(AnalysisMode.MANUAL, url=url))

    def start_manual(
        self, segments: list[TranscriptSegment], url: str = "", title: str = ""
    ) -> None:
        self.last_url, self.last_title = url, title
        self._start(AnalysisRequest(AnalysisMode.MANUAL, url=url, title=title, segments=segments))

    def _start(self, request: AnalysisRequest) -> None:
        if self.is_running:
            return
        worker = AnalysisWorker(request, self.source, parent=self)
        worker.progress.connect(self.analysis_progress)
        worker.done.connect(self._on_done)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self.analysis_cancelled)
        worker.finished.connect(self._on_thread_finished)
        self._worker = worker
        self.analysis_started.emit()
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()

    def wait(self, ms: int = 3000) -> None:
        """Block until the worker stops (used on shutdown)."""
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(ms)

    def _on_done(self, analysis: Analysis) -> None:
        try:
            self.repo.save(analysis)
        except Exception:  # noqa: BLE001 - results are still shown without history
            log.exception("Could not save analysis")
        self.history_changed.emit()
        self.analysis_finished.emit(analysis)

    def _on_failed(self, code: str) -> None:
        self.analysis_failed.emit(error_message(code), code in MANUAL_FALLBACK_CODES)

    def _on_thread_finished(self) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()

    # --- history and Shorts ----------------------------------------------
    def history(self, limit: int | None = None) -> list[HistoryItem]:
        return self.repo.list_history(limit)

    def open_analysis(self, analysis_id: int) -> Analysis | None:
        return self.repo.get(analysis_id)

    def delete_analysis(self, analysis_id: int) -> None:
        self.repo.delete(analysis_id)
        self.history_changed.emit()

    def save_short_text(self, short: Short, hook: str, title: str, description: str) -> None:
        short.hook, short.title, short.description = hook, title, description
        short.is_edited = True
        if short.id is not None:
            self.repo.update_short_text(short.id, hook, title, description)

    def set_favorite(self, short: Short, value: bool) -> None:
        short.is_favorite = value
        if short.id is not None:
            self.repo.set_favorite(short.id, value)

    def delete_short(self, short: Short) -> None:
        if short.id is not None:
            self.repo.delete_short(short.id)
        self.history_changed.emit()

    # --- settings ---------------------------------------------------------
    def update_settings(self, settings: Settings) -> None:
        self.settings = settings.normalized()
        try:
            self._settings_store.save(self.settings)
        except OSError:
            log.exception("Could not save settings")
        self.settings_changed.emit(self.settings)
