"""Parse transcripts from plain text, SRT and VTT into timed segments."""

from __future__ import annotations

import re
from pathlib import Path

from youtube_factory.models import TranscriptSegment

WORDS_PER_SECOND = 2.5  # ~150 words per minute, used for untimed text
MAX_FILE_BYTES = 5 * 1024 * 1024

_TIME_RE = re.compile(
    r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*"
    r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
)
_TAG_RE = re.compile(r"<[^>]+>")
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


class TranscriptError(ValueError):
    """Raised when a transcript is empty or cannot be read."""


def _to_sec(h: str | None, m: str, s: str, ms: str) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_timed(text: str) -> list[TranscriptSegment]:
    """Parse SRT or VTT content. Returns an empty list if no cues are found."""
    segments: list[TranscriptSegment] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            match = _TIME_RE.search(line)
            if not match:
                continue
            g = match.groups()
            start = _to_sec(g[0], g[1], g[2], g[3])
            end = _to_sec(g[4], g[5], g[6], g[7])
            body = " ".join(lines[i + 1 :])
            body = _TAG_RE.sub("", body).strip()
            if body and end >= start:
                segments.append(TranscriptSegment(start, end, body))
            break
    return segments


def parse_plain(text: str) -> list[TranscriptSegment]:
    """Split untimed text into sentences with timing estimated from word count."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    sentences = [s.strip() for s in _SENTENCE_RE.split(cleaned) if s.strip()]
    segments: list[TranscriptSegment] = []
    cursor = 0.0
    for sentence in sentences:
        duration = max(1.5, len(sentence.split()) / WORDS_PER_SECOND)
        segments.append(TranscriptSegment(cursor, cursor + duration, sentence))
        cursor += duration
    return segments


def parse_transcript(text: str) -> tuple[list[TranscriptSegment], bool]:
    """Parse any supported format. Returns (segments, has_real_timestamps)."""
    if not text or not text.strip():
        raise TranscriptError("empty")
    text = text.lstrip("﻿")
    timed = parse_timed(text)
    if timed:
        return _merge_duplicates(timed), True
    plain = parse_plain(text)
    if not plain:
        raise TranscriptError("empty")
    return plain, False


def _merge_duplicates(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Drop immediately repeated cues, common in auto-generated captions."""
    result: list[TranscriptSegment] = []
    for seg in segments:
        if result and result[-1].text == seg.text:
            result[-1].end_sec = max(result[-1].end_sec, seg.end_sec)
        else:
            result.append(seg)
    return result


def read_transcript_file(path: Path) -> tuple[list[TranscriptSegment], bool]:
    """Read a .txt, .srt or .vtt file (UTF-8, BOM tolerated)."""
    path = Path(path)
    if path.suffix.lower() not in {".txt", ".srt", ".vtt"}:
        raise TranscriptError("unsupported_type")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise TranscriptError("unreadable") from exc
    if size > MAX_FILE_BYTES:
        raise TranscriptError("too_large")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TranscriptError("unreadable") from exc
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return parse_transcript(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise TranscriptError("unreadable")
