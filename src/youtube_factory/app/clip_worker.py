"""Background worker that makes vertical clips one after another."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from youtube_factory.services import clipper, tools
from youtube_factory.services.clipper import ClipCancelled, ClipError, ClipRequest

log = logging.getLogger(__name__)


class ClipWorker(QThread):
    preparing = Signal(str, float)  # tool title, 0..1 (first-run download)
    item_started = Signal(int)  # index in the batch
    item_progress = Signal(int, float)
    item_done = Signal(int, str)  # index, file path
    item_failed = Signal(int, str)  # index, error code
    batch_done = Signal(int, int, bool)  # ok, failed, cancelled

    def __init__(
        self,
        requests: list[ClipRequest],
        make_clip: Callable[..., Path] = clipper.make_clip,
        ensure_tools: Callable[..., None] = tools.ensure_tools,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._requests = requests
        self._make_clip = make_clip
        self._ensure_tools = ensure_tools

    def run(self) -> None:
        ok = failed = 0
        cancelled = False
        try:
            self._ensure_tools(self.preparing.emit, self.isInterruptionRequested)
        except tools.ToolsCancelled:
            self.batch_done.emit(0, 0, True)
            return
        except tools.ToolsError as exc:
            for i in range(len(self._requests)):
                self.item_failed.emit(i, exc.code)
            self.batch_done.emit(0, len(self._requests), False)
            return
        for i, req in enumerate(self._requests):
            if self.isInterruptionRequested():
                cancelled = True
                break
            self.item_started.emit(i)
            try:
                path = self._make_clip(
                    req,
                    lambda f, i=i: self.item_progress.emit(i, f),
                    self.isInterruptionRequested,
                )
            except ClipCancelled:
                cancelled = True
                break
            except ClipError as exc:
                failed += 1
                self.item_failed.emit(i, exc.code)
            except Exception:  # noqa: BLE001 - one bad clip must not stop the batch
                log.exception("Clip %s failed", i)
                failed += 1
                self.item_failed.emit(i, "unknown")
            else:
                ok += 1
                self.item_done.emit(i, str(path))
        self.batch_done.emit(ok, failed, cancelled)
