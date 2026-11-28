"""YouTube access through yt-dlp: video details, thumbnail and captions.

No API keys are needed. Captions are taken in this order: written by the author in
Russian or English, then automatic captions in the video's own language.
Network access is injected so tests can run without it.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from collections.abc import Callable
from typing import Any

from youtube_factory.integrations.base import LoadedVideo, VideoSourceError
from youtube_factory.models import TranscriptSegment, VideoInfo
from youtube_factory.services.transcript_parser import parse_timed
from youtube_factory.services.url_parser import canonical_url, extract_video_id

log = logging.getLogger(__name__)

PREFERRED_LANGS = ("ru", "en")
MAX_CAPTION_BYTES = 8 * 1024 * 1024
NET_TIMEOUT_S = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

Extract = Callable[[str], dict[str, Any]]
Fetch = Callable[[str], bytes]

# Fragments of yt-dlp error text mapped to stable error codes (lower case).
_ERROR_HINTS: tuple[tuple[str, str], ...] = (
    ("not a bot", "bot_check"),
    ("private video", "video_private"),
    ("members-only", "video_private"),
    ("sign in to confirm your age", "age_restricted"),
    ("age-restricted", "age_restricted"),
    ("video unavailable", "video_unavailable"),
    ("has been removed", "video_unavailable"),
    ("is not available", "video_unavailable"),
    ("premieres in", "video_live"),
    ("live event", "video_live"),
    ("getaddrinfo", "net_offline"),
    ("name or service not known", "net_offline"),
    ("network is unreachable", "net_offline"),
    ("timed out", "net_offline"),
    ("connection", "net_offline"),
    ("unable to connect", "net_offline"),
    ("proxy", "net_offline"),
    ("unable to download webpage", "net_offline"),
)


def classify_error(message: str) -> str:
    """Turn a yt-dlp / urllib error text into one of our error codes."""
    text = message.lower()
    for fragment, code in _ERROR_HINTS:
        if fragment in text:
            return code
    return "net_error"


def _tool_options() -> dict[str, Any]:
    """Use Deno when it is installed; YouTube needs it for some videos."""
    from youtube_factory.services.clipper import ytdlp_tool_options

    options = ytdlp_tool_options()
    return {"js_runtimes": options["js_runtimes"]} if "js_runtimes" in options else {}


def _default_extract(url: str) -> dict[str, Any]:
    import yt_dlp

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": NET_TIMEOUT_S,
        "retries": 2,
        **_tool_options(),
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise VideoSourceError("video_unavailable")
    return info


def _default_fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=NET_TIMEOUT_S) as response:  # noqa: S310
        data = response.read(MAX_CAPTION_BYTES + 1)
    if len(data) > MAX_CAPTION_BYTES:
        raise VideoSourceError("net_error")
    return data


def parse_json3(data: bytes) -> list[TranscriptSegment]:
    """Parse YouTube's json3 caption format into timed segments."""
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return []
    segments: list[TranscriptSegment] = []
    for event in payload.get("events", []):
        pieces = event.get("segs")
        if not pieces or event.get("aAppend"):
            continue
        text = "".join(str(p.get("utf8", "")) for p in pieces).replace("\n", " ")
        text = " ".join(text.split())
        if not text:
            continue
        start = float(event.get("tStartMs", 0)) / 1000
        end = start + float(event.get("dDurationMs", 0)) / 1000
        if segments and segments[-1].text == text:
            segments[-1].end_sec = max(segments[-1].end_sec, end)
        else:
            segments.append(TranscriptSegment(start, max(end, start), text))
    return segments


def _formats_by_ext(entries: list[dict[str, Any]]) -> dict[str, str]:
    return {e.get("ext", ""): e.get("url", "") for e in entries if e.get("url")}


def choose_captions(info: dict[str, Any]) -> tuple[str, bool, dict[str, str]] | None:
    """Pick the best caption track. Returns (language, is_automatic, {ext: url})."""
    manual: dict[str, list] = info.get("subtitles") or {}
    auto: dict[str, list] = info.get("automatic_captions") or {}
    own = str(info.get("language") or "").split("-")[0]
    langs = [*PREFERRED_LANGS, own] if own and own not in PREFERRED_LANGS else list(PREFERRED_LANGS)
    if own:  # the video's own language goes first
        langs = [own, *[x for x in langs if x != own]]

    for lang in langs:
        if manual.get(lang):
            return lang, False, _formats_by_ext(manual[lang])
    for lang in langs:
        # "<lang>-orig" is the speech-recognised original, not a machine translation.
        for key in (f"{lang}-orig", lang):
            if auto.get(key):
                return lang, True, _formats_by_ext(auto[key])
    return None


class YouTubeSource:
    def __init__(self, extract: Extract | None = None, fetch: Fetch | None = None) -> None:
        self._extract = extract or _default_extract
        self._fetch = fetch or _default_fetch

    def load(self, url: str) -> LoadedVideo:
        video_id = extract_video_id(url)
        page = canonical_url(video_id)
        try:
            info = self._extract(page)
        except VideoSourceError:
            raise
        except Exception as exc:  # noqa: BLE001 - yt-dlp raises several unrelated types
            code = classify_error(str(exc))
            log.warning("Could not load %s: %s", video_id, exc)
            raise VideoSourceError(code) from exc

        if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming"}:
            raise VideoSourceError("video_live")

        chosen = choose_captions(info)
        if chosen is None:
            raise VideoSourceError("no_transcript")
        language, automatic, formats = chosen
        segments = self._download_captions(formats)
        if not segments:
            raise VideoSourceError("no_transcript")

        duration = int(info.get("duration") or segments[-1].end_sec)
        video = VideoInfo(
            video_id=video_id,
            url=page,
            title=str(info.get("title") or ""),
            channel=str(info.get("channel") or info.get("uploader") or ""),
            duration_sec=duration,
            thumbnail=self._thumbnail(video_id),
        )
        return LoadedVideo(video, segments, language, automatic)

    def _download_captions(self, formats: dict[str, str]) -> list[TranscriptSegment]:
        try:
            if formats.get("json3"):
                segments = parse_json3(self._fetch(formats["json3"]))
                if segments:
                    return segments
            if formats.get("vtt"):
                return parse_timed(self._fetch(formats["vtt"]).decode("utf-8-sig", "replace"))
        except VideoSourceError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not download captions: %s", exc)
            raise VideoSourceError(classify_error(str(exc))) from exc
        return []

    def _thumbnail(self, video_id: str) -> bytes | None:
        """Best effort: a missing picture must never fail the analysis."""
        try:
            return self._fetch(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg")
        except Exception:  # noqa: BLE001
            return None
