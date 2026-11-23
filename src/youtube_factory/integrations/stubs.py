"""Placeholder adapters. They report clearly that the integration is not available."""

from __future__ import annotations

from youtube_factory.integrations.base import IntegrationUnavailableError
from youtube_factory.models import Short, TranscriptSegment, VideoInfo


class YouTubeApiStub:
    def fetch(self, video_id: str) -> VideoInfo:
        raise IntegrationUnavailableError("youtube_api")


class TranscriptServiceStub:
    def fetch(self, video_id: str, language: str = "ru") -> list[TranscriptSegment]:
        raise IntegrationUnavailableError("transcript_service")


class LlmStub:
    def refine(self, segments: list[TranscriptSegment], draft: list[Short]) -> list[Short]:
        raise IntegrationUnavailableError("llm")
