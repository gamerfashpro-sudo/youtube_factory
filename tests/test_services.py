import csv
import json

import pytest

from youtube_factory.models import Short, TranscriptSegment, VideoInfo
from youtube_factory.services import analyzer, demo, exporter
from youtube_factory.services.transcript_parser import (
    TranscriptError,
    parse_transcript,
    read_transcript_file,
)
from youtube_factory.services.url_parser import InvalidUrlError, extract_video_id

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "text",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&t=42s&list=abc",
        f"https://youtu.be/{VID}?si=xyz",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"m.youtube.com/watch?v={VID}",
        f"  {VID}  ",
    ],
)
def test_extract_video_id(text):
    assert extract_video_id(text) == VID


@pytest.mark.parametrize(
    "text", ["", "   ", "hello", "https://example.com/watch?v=" + VID,
             "https://www.youtube.com/watch?v=short", "https://www.youtube.com/"]
)
def test_extract_video_id_invalid(text):
    with pytest.raises(InvalidUrlError):
        extract_video_id(text)


SRT = """1
00:00:01,000 --> 00:00:05,500
Привет, это <i>тест</i>.

2
00:00:05,500 --> 00:00:10,000
Второй субтитр!
"""

VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Первая строка

00:00:04.000 --> 00:01:10.250
Вторая строка
"""


def test_parse_srt():
    segs, timed = parse_transcript(SRT)
    assert timed
    assert len(segs) == 2
    assert segs[0].text == "Привет, это тест."
    assert segs[1].start_sec == 5.5


def test_parse_vtt_with_bom():
    segs, timed = parse_transcript("﻿" + VTT)
    assert timed and len(segs) == 2
    assert segs[1].end_sec == pytest.approx(70.25)


def test_parse_plain_has_estimated_timing():
    segs, timed = parse_transcript("Первое предложение. Второе предложение! Третье?")
    assert not timed
    assert len(segs) == 3
    assert segs[1].start_sec == pytest.approx(segs[0].end_sec)


def test_empty_transcript():
    with pytest.raises(TranscriptError):
        parse_transcript("  \n ")


def test_read_file_cyrillic_name_and_cp1251(tmp_path):
    p = tmp_path / "субтитры.srt"
    p.write_bytes(SRT.encode("cp1251"))
    segs, timed = read_transcript_file(p)
    assert timed and "тест" in segs[0].text


def test_read_file_wrong_type(tmp_path):
    p = tmp_path / "x.docx"
    p.write_text("a")
    with pytest.raises(TranscriptError):
        read_transcript_file(p)


def test_read_file_missing(tmp_path):
    with pytest.raises(TranscriptError):
        read_transcript_file(tmp_path / "нет.txt")


def test_demo_analysis_is_valid_and_deterministic():
    segs = demo.demo_segments()
    a = analyzer.analyze_segments(segs)
    b = analyzer.analyze_segments(segs)
    assert [s.title for s in a] == [s.title for s in b]
    assert 5 <= len(a) <= 10
    for s in a:
        assert 0 <= s.score <= 100
        assert s.hook and s.title and s.description and s.reason
        assert s.hashtags[0] == "#shorts"
        assert 20 <= s.end_sec - s.start_sec <= 60.5
    spans = sorted((s.start_sec, s.end_sec) for s in a)
    assert all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1))


def test_analysis_too_short():
    with pytest.raises(analyzer.AnalysisError):
        analyzer.analyze_segments([TranscriptSegment(0, 5, "слишком коротко")])


def test_analysis_cancel():
    with pytest.raises(analyzer.AnalysisCancelled):
        analyzer.analyze_segments(demo.demo_segments(), is_cancelled=lambda: True)


def test_format_range():
    assert analyzer.format_range(134, 182) == "02:14 – 03:02"
    assert analyzer.format_time(3725) == "1:02:05"


def _shorts():
    return [Short(134, 182, "Хук «тест»", "Название; с точкой", "Описание\nв две строки",
                  ["#shorts", "#тест"], 77, "Причина", is_favorite=True)]


def test_export_csv_has_bom_and_cyrillic(tmp_path):
    p = tmp_path / "экспорт.csv"
    exporter.export_csv(p, _shorts())
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(raw.decode("utf-8-sig").splitlines(), delimiter=";"))
    assert rows[0] == exporter.CSV_HEADERS
    assert rows[1][0] == "02:14 – 03:02" and rows[1][-1] == "да"


def test_export_json_roundtrip(tmp_path):
    p = tmp_path / "out.json"
    video = VideoInfo(VID, "https://youtu.be/" + VID, "Заголовок", "Канал", 300)
    exporter.export_json(p, video, _shorts())
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["video"]["title"] == "Заголовок"
    assert data["shorts"][0]["score"] == 77
    assert "Хук" in p.read_text(encoding="utf-8")


def test_export_error(tmp_path):
    with pytest.raises(exporter.ExportError):
        exporter.export_csv(tmp_path / "нет" / "папки" / "a.csv", _shorts())


def test_short_to_text_contains_all_fields():
    text = exporter.short_to_text(_shorts()[0])
    for part in ("02:14 – 03:02", "Хук", "Название", "Описание", "#тест", "77/100", "Причина"):
        assert part in text
