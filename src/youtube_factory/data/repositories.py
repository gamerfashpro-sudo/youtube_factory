"""Data access for analyses and Shorts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from youtube_factory.models import Analysis, AnalysisMode, Short, VideoInfo


@dataclass(slots=True)
class HistoryItem:
    id: int
    created_at: datetime
    mode: AnalysisMode
    title: str
    channel: str
    url: str
    shorts_count: int


def _row_to_short(row: sqlite3.Row) -> Short:
    return Short(
        id=row["id"],
        analysis_id=row["analysis_id"],
        start_sec=row["start_sec"],
        end_sec=row["end_sec"],
        hook=row["hook"],
        title=row["title"],
        description=row["description"],
        hashtags=json.loads(row["hashtags"]),
        score=row["score"],
        reason=row["reason"],
        is_favorite=bool(row["is_favorite"]),
        is_edited=bool(row["is_edited"]),
    )


class AnalysisRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, analysis: Analysis) -> Analysis:
        """Insert the analysis and its Shorts; fills in the generated IDs."""
        v = analysis.video
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO analyses (created_at, mode, video_id, url, title, channel,"
                " duration_sec, thumbnail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    analysis.created_at.isoformat(timespec="seconds"),
                    str(analysis.mode),
                    v.video_id,
                    v.url,
                    v.title,
                    v.channel,
                    v.duration_sec,
                    v.thumbnail,
                ),
            )
            analysis.id = int(cur.lastrowid)
            for position, short in enumerate(analysis.shorts):
                short.analysis_id = analysis.id
                short.id = self._insert_short(short, position)
        return analysis

    def _insert_short(self, s: Short, position: int) -> int:
        cur = self._conn.execute(
            "INSERT INTO shorts (analysis_id, position, start_sec, end_sec, hook, title,"
            " description, hashtags, score, reason, is_favorite, is_edited)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                s.analysis_id,
                position,
                s.start_sec,
                s.end_sec,
                s.hook,
                s.title,
                s.description,
                json.dumps(s.hashtags, ensure_ascii=False),
                s.score,
                s.reason,
                int(s.is_favorite),
                int(s.is_edited),
            ),
        )
        return int(cur.lastrowid)

    def get(self, analysis_id: int) -> Analysis | None:
        row = self._conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        if row is None:
            return None
        shorts = [
            _row_to_short(r)
            for r in self._conn.execute(
                "SELECT * FROM shorts WHERE analysis_id = ? ORDER BY position, id",
                (analysis_id,),
            )
        ]
        return Analysis(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            mode=AnalysisMode(row["mode"]),
            video=VideoInfo(
                video_id=row["video_id"],
                url=row["url"],
                title=row["title"],
                channel=row["channel"],
                duration_sec=row["duration_sec"],
                thumbnail=row["thumbnail"],
            ),
            shorts=shorts,
        )

    def list_history(self, limit: int | None = None) -> list[HistoryItem]:
        sql = (
            "SELECT a.id, a.created_at, a.mode, a.title, a.channel, a.url,"
            " (SELECT COUNT(*) FROM shorts s WHERE s.analysis_id = a.id) AS cnt"
            " FROM analyses a ORDER BY a.created_at DESC, a.id DESC"
        )
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        return [
            HistoryItem(
                id=r["id"],
                created_at=datetime.fromisoformat(r["created_at"]),
                mode=AnalysisMode(r["mode"]),
                title=r["title"],
                channel=r["channel"],
                url=r["url"],
                shorts_count=r["cnt"],
            )
            for r in self._conn.execute(sql, params)
        ]

    def delete(self, analysis_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))

    def update_short_text(self, short_id: int, hook: str, title: str, description: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE shorts SET hook = ?, title = ?, description = ?, is_edited = 1"
                " WHERE id = ?",
                (hook, title, description, short_id),
            )

    def set_favorite(self, short_id: int, value: bool) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE shorts SET is_favorite = ? WHERE id = ?", (int(value), short_id)
            )

    def delete_short(self, short_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shorts WHERE id = ?", (short_id,))
