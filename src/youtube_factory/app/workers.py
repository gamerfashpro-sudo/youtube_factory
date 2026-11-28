"""Background analysis worker. All heavy work runs off the UI thread."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from youtube_factory import strings_ru as ru
from youtube_factory.integrations.base import (
    IntegrationUnavailableError,
    VideoSource,
    VideoSourceError,
)
from youtube_factory.models import Analysis, AnalysisMode, TranscriptSegment, VideoInfo
from youtube_factory.services import demo
from youtube_factory.services.analyzer import (
    AnalysisCancelled,
    AnalysisError,
    analyze_segments,
)
from youtube_factory.services.transcript_parser import TranscriptError
from youtube_factory.services.url_parser import InvalidUrlError, canonical_url, extract_video_id

STEP_PAUSE_MS = 180

ERROR_MESSAGES = {
    "empty_url": ru.ERR_EMPTY_URL,
    "not_youtube": ru.ERR_NOT_YOUTUBE,
    "no_video_id": ru.ERR_NO_VIDEO_ID,
    "no_transcript": ru.ERR_NO_TRANSCRIPT,
    "transcript_empty": ru.ERR_TRANSCRIPT_EMPTY,
    "unsupported_type": ru.ERR_TRANSCRIPT_TYPE,
    "unreadable": ru.ERR_TRANSCRIPT_UNREADABLE,
    "too_large": ru.ERR_TRANSCRIPT_LARGE,
    "too_short": ru.ERR_TOO_SHORT,
    "no_candidates": ru.ERR_NO_CANDIDATES,
    "net_offline": ru.ERR_NET_OFFLINE,
    "net_error": ru.ERR_NET_ERROR,
    "video_unavailable": ru.ERR_VIDEO_UNAVAILABLE,
    "video_private": ru.ERR_VIDEO_PRIVATE,
    "age_restricted": ru.ERR_AGE_RESTRICTED,
    "video_live": ru.ERR_VIDEO_LIVE,
    "bot_check": ru.ERR_BOT_CHECK,
}

# Short reasons shown on a clip card (they follow "Не получилось: ").
CLIP_ERROR_REASONS = {
    "clip_download_failed": ru.ERR_CLIP_DOWNLOAD,
    "clip_convert_failed": ru.ERR_CLIP_CONVERT,
    "ffmpeg_missing": ru.ERR_CLIP_FFMPEG,
    "tools_download_failed": ru.ERR_TOOLS_DOWNLOAD,
    "tools_corrupt": ru.ERR_TOOLS_CORRUPT,
    "tools_missing": ru.ERR_CLIP_FFMPEG,
    "clip_folder": ru.ERR_CLIP_FOLDER,
    "no_source": ru.ERR_CLIP_NO_SOURCE,
    "net_offline": ru.ERR_NET_OFFLINE.rstrip(".").lower(),
    "bot_check": ru.ERR_BOT_CHECK,
    "video_unavailable": ru.ERR_VIDEO_UNAVAILABLE.rstrip(".").lower(),
    "video_private": ru.ERR_VIDEO_PRIVATE.rstrip(".").lower(),
    "age_restricted": ru.ERR_AGE_RESTRICTED,
    "video_live": ru.ERR_VIDEO_LIVE,
}


def clip_error_reason(code: str) -> str:
    return CLIP_ERROR_REASONS.get(code, ru.ERR_UNKNOWN.rstrip(".").lower())


# Errors after which pasting a transcript by hand can still get the user to a result.
MANUAL_FALLBACK_CODES = frozenset({"no_transcript", "net_error", "bot_check"})


def error_message(code: str) -> str:
    return ERROR_MESSAGES.get(code, ru.ERR_UNKNOWN)


def error_code(exc: BaseException) -> str:
    """Map a domain exception to a stable error code."""
    if isinstance(exc, InvalidUrlError):
        return str(exc) if str(exc) in ERROR_MESSAGES else "no_video_id"
    if isinstance(exc, TranscriptError):
        return "transcript_empty" if str(exc) == "empty" else str(exc)
    if isinstance(exc, AnalysisError):
        return str(exc)
    if isinstance(exc, VideoSourceError):
        return exc.code
    if isinstance(exc, IntegrationUnavailableError):
        return "no_transcript"
    return "unknown"


@dataclass(slots=True)
class AnalysisRequest:
    mode: AnalysisMode
    url: str = ""
    title: str = ""
    segments: list[TranscriptSegment] | None = None


class AnalysisWorker(QThread):
    progress = Signal(int)
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        request: AnalysisRequest,
        source: VideoSource | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._source = source

    def run(self) -> None:
        try:
            analysis = self._run()
        except AnalysisCancelled:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 - reported to the user, logged by the caller
            code = error_code(exc)
            if code == "unknown":
                import logging

                logging.getLogger(__name__).exception("Analysis failed")
            self.failed.emit(code)
        else:
            self.done.emit(analysis)

    def _pause(self) -> None:
        for _ in range(3):
            if self.isInterruptionRequested():
                raise AnalysisCancelled
            self.msleep(STEP_PAUSE_MS // 3)

    def _run(self) -> Analysis:
        req = self._request
        self.progress.emit(0)
        if req.mode == AnalysisMode.DEMO:
            video = demo.demo_video()
            segments = demo.demo_segments()
            self._pause()
        elif req.segments is None and req.url.strip():
            video, segments = self._load_from_youtube(req.url)
            self.progress.emit(1)
        else:
            video = self._video_from_request()
            self._pause()
            self.progress.emit(1)
            segments = req.segments or []
            video.duration_sec = int(segments[-1].end_sec) if segments else 0
        self.progress.emit(1)
        self._pause()
        shorts = analyze_segments(
            segments,
            progress=self.progress.emit,
            is_cancelled=self.isInterruptionRequested,
        )
        self.progress.emit(4)
        self._pause()
        return Analysis(mode=req.mode, video=video, shorts=shorts)

    def _load_from_youtube(self, url: str) -> tuple[VideoInfo, list[TranscriptSegment]]:
        source = self._source
        if source is None:
            from youtube_factory.integrations.youtube import YouTubeSource

            source = YouTubeSource()
        loaded = source.load(url)
        if self.isInterruptionRequested():
            raise AnalysisCancelled
        return loaded.video, loaded.segments

    def _video_from_request(self) -> VideoInfo:
        req = self._request
        title = req.title.strip() or ru.DEFAULT_VIDEO_TITLE
        if req.url.strip():
            video_id = extract_video_id(req.url)
            return VideoInfo(video_id, canonical_url(video_id), title)
        return VideoInfo("", "", title)
