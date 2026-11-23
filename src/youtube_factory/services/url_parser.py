"""YouTube URL validation and video ID extraction (offline)."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_PATH_PREFIXES = ("shorts", "embed", "live", "v")


class InvalidUrlError(ValueError):
    """Raised when the text is not a recognisable YouTube video URL."""


def extract_video_id(text: str) -> str:
    """Return the 11-character video ID from a YouTube URL or a bare ID."""
    value = (text or "").strip()
    if not value:
        raise InvalidUrlError("empty")
    if _ID_RE.match(value):
        return value
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    candidate = ""
    if host in _SHORT_HOSTS:
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in _HOSTS:
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[0] == "watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] in _PATH_PREFIXES:
            candidate = parts[1]
    else:
        raise InvalidUrlError("not_youtube")
    if not _ID_RE.match(candidate):
        raise InvalidUrlError("no_video_id")
    return candidate


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
