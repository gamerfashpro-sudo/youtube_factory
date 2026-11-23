"""Export Shorts to JSON and CSV (CSV is UTF-8 with BOM for Excel)."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path

from youtube_factory.models import Short, VideoInfo
from youtube_factory.services.analyzer import format_range

CSV_HEADERS = [
    "Время",
    "Хук",
    "Название",
    "Описание",
    "Хэштеги",
    "Потенциал",
    "Почему сработает",
    "Избранное",
]


class ExportError(OSError):
    """Raised when a file cannot be written."""


def short_to_dict(short: Short) -> dict:
    return {
        "start_sec": round(short.start_sec, 2),
        "end_sec": round(short.end_sec, 2),
        "time_range": format_range(short.start_sec, short.end_sec),
        "hook": short.hook,
        "title": short.title,
        "description": short.description,
        "hashtags": list(short.hashtags),
        "score": short.score,
        "reason": short.reason,
        "is_favorite": short.is_favorite,
    }


def short_to_text(short: Short) -> str:
    """Full plain-text form used by the 'copy' button."""
    return (
        f"{format_range(short.start_sec, short.end_sec)}\n"
        f"Хук: {short.hook}\n"
        f"Название: {short.title}\n"
        f"Описание: {short.description}\n"
        f"Хэштеги: {' '.join(short.hashtags)}\n"
        f"Потенциал: {short.score}/100\n"
        f"Почему сработает: {short.reason}"
    )


def export_json(path: Path, video: VideoInfo, shorts: Sequence[Short]) -> None:
    payload = {
        "video": {
            "id": video.video_id,
            "url": video.url,
            "title": video.title,
            "channel": video.channel,
            "duration_sec": video.duration_sec,
        },
        "shorts": [short_to_dict(s) for s in shorts],
    }
    try:
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise ExportError(str(exc)) from exc


def export_csv(path: Path, shorts: Sequence[Short]) -> None:
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(CSV_HEADERS)
            for s in shorts:
                writer.writerow(
                    [
                        format_range(s.start_sec, s.end_sec),
                        s.hook,
                        s.title,
                        s.description,
                        " ".join(s.hashtags),
                        s.score,
                        s.reason,
                        "да" if s.is_favorite else "нет",
                    ]
                )
    except OSError as exc:
        raise ExportError(str(exc)) from exc
