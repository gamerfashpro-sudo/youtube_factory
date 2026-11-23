"""Adapter interfaces for future integrations.

Version 0.1.0 ships without network adapters. Anything implementing these
protocols can be plugged in later without touching the UI or the analyzer.
"""

from __future__ import annotations

from typing import Protocol

from youtube_factory.models import Short, TranscriptSegment, VideoInfo


class IntegrationUnavailableError(RuntimeError):
    """Raised by stub adapters that are not implemented yet."""


class VideoMetadataProvider(Protocol):
    """Fetches title, channel, duration and thumbnail (e.g. YouTube Data API)."""

    def fetch(self, video_id: str) -> VideoInfo: ...


class TranscriptProvider(Protocol):
    """Fetches a transcript for a video ID (e.g. a transcript extraction service)."""

    def fetch(self, video_id: str, language: str = "ru") -> list[TranscriptSegment]: ...


class LlmProvider(Protocol):
    """Improves heuristic Shorts with a local or cloud language model."""

    def refine(self, segments: list[TranscriptSegment], draft: list[Short]) -> list[Short]: ...
