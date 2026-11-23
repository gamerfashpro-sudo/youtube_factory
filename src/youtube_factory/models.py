"""Domain models. Plain dataclasses, no Qt or database dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class AnalysisMode(StrEnum):
    DEMO = "demo"
    MANUAL = "manual"


@dataclass(slots=True)
class VideoInfo:
    video_id: str
    url: str
    title: str = ""
    channel: str = ""
    duration_sec: int = 0
    thumbnail: bytes | None = None


@dataclass(slots=True)
class TranscriptSegment:
    start_sec: float
    end_sec: float
    text: str


@dataclass(slots=True)
class Short:
    start_sec: float
    end_sec: float
    hook: str
    title: str
    description: str
    hashtags: list[str] = field(default_factory=list)
    score: int = 0
    reason: str = ""
    is_favorite: bool = False
    is_edited: bool = False
    id: int | None = None
    analysis_id: int | None = None

    def __post_init__(self) -> None:
        self.score = max(0, min(100, int(self.score)))


@dataclass(slots=True)
class Analysis:
    mode: AnalysisMode
    video: VideoInfo
    shorts: list[Short] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    id: int | None = None
