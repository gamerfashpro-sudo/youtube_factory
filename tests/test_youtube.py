"""YouTube source tests. All network access is replaced with fakes."""

import json

import pytest

from youtube_factory.integrations.base import VideoSourceError
from youtube_factory.integrations.youtube import (
    YouTubeSource,
    choose_captions,
    classify_error,
    parse_json3,
)

VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def json3(*events: dict) -> bytes:
    return json.dumps({"events": list(events)}).encode()


def event(start_ms: int, dur_ms: int, text: str, **extra) -> dict:
    return {"tStartMs": start_ms, "dDurationMs": dur_ms, "segs": [{"utf8": text}], **extra}


def info(**overrides) -> dict:
    base = {
        "title": "Тестовое видео",
        "channel": "Канал",
        "duration": 300,
        "subtitles": {},
        "automatic_captions": {},
    }
    return {**base, **overrides}


def source(extract_info: dict, files: dict[str, bytes] | None = None) -> YouTubeSource:
    files = files or {}

    def fetch(url: str) -> bytes:
        if url not in files:
            raise OSError("no such file in test")
        return files[url]

    return YouTubeSource(extract=lambda _url: extract_info, fetch=fetch)


# --- parsing ---------------------------------------------------------------
def test_parse_json3_builds_timed_segments():
    data = json3(
        {"tStartMs": 0, "wWinId": 1},  # window definition without text
        event(1000, 2500, "Привет,\nмир"),
        event(3500, 500, "\n", aAppend=1),
        event(4000, 1000, "  второй   фрагмент "),
    )
    segs = parse_json3(data)
    assert [(s.start_sec, s.end_sec, s.text) for s in segs] == [
        (1.0, 3.5, "Привет, мир"),
        (4.0, 5.0, "второй фрагмент"),
    ]


def test_parse_json3_merges_repeated_lines_and_survives_garbage():
    segs = parse_json3(json3(event(0, 1000, "то же"), event(1000, 1000, "то же")))
    assert len(segs) == 1 and segs[0].end_sec == 2.0
    assert parse_json3(b"not json") == []
    assert parse_json3(b"\xff\xfe") == []


# --- choosing captions -------------------------------------------------------
def test_manual_captions_beat_automatic_ones():
    lang, auto, _ = choose_captions(
        info(
            subtitles={"en": [{"ext": "json3", "url": "m"}]},
            automatic_captions={"ru": [{"ext": "json3", "url": "a"}]},
        )
    )
    assert (lang, auto) == ("en", False)


def test_russian_is_preferred_over_english():
    lang, auto, formats = choose_captions(
        info(subtitles={"en": [{"ext": "json3", "url": "e"}], "ru": [{"ext": "json3", "url": "r"}]})
    )
    assert (lang, auto, formats["json3"]) == ("ru", False, "r")


def test_automatic_captions_use_the_original_track_not_a_translation():
    lang, auto, formats = choose_captions(
        info(
            language="de",
            automatic_captions={
                "ru": [{"ext": "json3", "url": "translated"}],
                "de-orig": [{"ext": "json3", "url": "original"}],
            },
        )
    )
    assert (lang, auto, formats["json3"]) == ("de", True, "original")


def test_no_captions_returns_none():
    assert choose_captions(info()) is None


# --- loading -------------------------------------------------------------------
def test_load_returns_video_details_and_segments():
    src = source(
        info(subtitles={"ru": [{"ext": "json3", "url": "cap"}]}),
        {
            "cap": json3(event(0, 2000, "первая фраза"), event(2000, 3000, "вторая фраза")),
            "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg": b"jpeg-bytes",
        },
    )
    loaded = src.load(VIDEO_URL)
    assert loaded.video.title == "Тестовое видео"
    assert loaded.video.channel == "Канал"
    assert loaded.video.duration_sec == 300
    assert loaded.video.thumbnail == b"jpeg-bytes"
    assert loaded.video.video_id == "dQw4w9WgXcQ"
    assert [s.text for s in loaded.segments] == ["первая фраза", "вторая фраза"]
    assert (loaded.language, loaded.automatic) == ("ru", False)


def test_missing_thumbnail_does_not_fail_the_load():
    src = source(
        info(subtitles={"ru": [{"ext": "json3", "url": "cap"}]}),
        {"cap": json3(event(0, 1000, "текст"))},
    )
    assert src.load(VIDEO_URL).video.thumbnail is None


def test_vtt_is_used_when_json3_is_missing():
    vtt = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello there\n"
    src = source(info(subtitles={"en": [{"ext": "vtt", "url": "v"}]}), {"v": vtt})
    assert src.load(VIDEO_URL).segments[0].text == "Hello there"


def test_video_without_captions_asks_for_manual_transcript():
    with pytest.raises(VideoSourceError) as err:
        source(info()).load(VIDEO_URL)
    assert err.value.code == "no_transcript"


def test_live_streams_are_rejected():
    with pytest.raises(VideoSourceError) as err:
        source(info(is_live=True)).load(VIDEO_URL)
    assert err.value.code == "video_live"


def test_extractor_failure_becomes_a_coded_error():
    def boom(_url):
        raise RuntimeError(
            "ERROR: [youtube] x: Private video. Sign in if you've been granted access"
        )

    with pytest.raises(VideoSourceError) as err:
        YouTubeSource(extract=boom).load(VIDEO_URL)
    assert err.value.code == "video_private"


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Sign in to confirm you’re not a bot", "bot_check"),
        ("Video unavailable. This video has been removed", "video_unavailable"),
        ("Sign in to confirm your age", "age_restricted"),
        ("<urlopen error [Errno 11001] getaddrinfo failed>", "net_offline"),
        ("Unable to connect to proxy", "net_offline"),
        ("HTTP Error 500", "net_error"),
        # Regression: yt-dlp appends "Confirm you are on the latest version" to every error.
        ("HTTP Error 500; Confirm you are on the latest version using yt-dlp -U", "net_error"),
    ],
)
def test_error_classification(text, code):
    assert classify_error(text) == code
