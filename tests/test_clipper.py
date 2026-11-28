"""Clip cutting and vertical conversion. Uses a generated video; no network."""

import re
import subprocess
from pathlib import Path

import pytest

from youtube_factory.services import clipper
from youtube_factory.services.clipper import (
    ClipCancelled,
    ClipError,
    ClipRequest,
    clip_path,
    make_clip,
    make_vertical,
    padded_range,
    vertical_filter,
)

try:
    FFMPEG = clipper.ffmpeg_path()
except ClipError:
    FFMPEG = ""

needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg is not available")


def make_source(path: Path, seconds: int = 3, size: str = "640x360") -> Path:
    """A small landscape test video with a tone, built by ffmpeg itself."""
    subprocess.run(  # noqa: S603
        [
            FFMPEG, "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size={size}:rate=25:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
    )  # fmt: skip
    return path


def video_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )  # noqa: S603
    match = re.search(r"Stream #\d+:\d+.*Video:.*?, (\d{3,5})x(\d{3,5})", out.stderr)
    assert match, out.stderr
    return int(match.group(1)), int(match.group(2))


def has_audio(path: Path) -> bool:
    out = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )  # noqa: S603
    return "Audio:" in out.stderr


# --- pure helpers --------------------------------------------------------------
def test_padded_range_adds_margins_and_stays_inside_the_video():
    assert padded_range(10, 20) == (9.6, 20.6)
    assert padded_range(0.1, 20) == (0.0, 20.6)
    assert padded_range(10, 20, duration=20.2) == (9.6, 20.2)
    start, end = padded_range(5, 5.0, duration=5.1)
    assert end - start >= 1.0


def test_file_names_are_safe_and_never_overwrite(tmp_path):
    req = ClipRequest("u", 'Видео: "тест"/1?', 3, 65.9, 100.2, tmp_path)
    first = clip_path(req)
    assert first.name.endswith("_03_65-100.mp4") and first.name.startswith("Видео")
    assert not re.search(r'[\\/:*?"<>|]', first.name)
    first.write_bytes(b"x")
    second = clip_path(req)
    assert second != first and second.name.endswith("_2.mp4")


@pytest.mark.parametrize("style", clipper.STYLES)
def test_every_style_targets_1080x1920(style):
    chain = vertical_filter(style)
    assert "1080" in chain and "1920" in chain


# --- real ffmpeg -----------------------------------------------------------------
@needs_ffmpeg
@pytest.mark.parametrize("style", clipper.STYLES)
def test_landscape_video_becomes_1080x1920_with_audio(tmp_path, style):
    src = make_source(tmp_path / "src.mp4")
    dst = tmp_path / f"{style}.mp4"
    seen: list[float] = []
    make_vertical(src, dst, style, 3.0, seen.append)
    assert video_size(dst) == (1080, 1920)
    assert has_audio(dst)
    assert seen and seen[-1] == 1.0 and seen == sorted(seen)


@needs_ffmpeg
def test_already_vertical_and_square_sources_also_work(tmp_path):
    for name, size in (("vertical", "360x640"), ("square", "480x480")):
        src = make_source(tmp_path / f"{name}.mp4", seconds=2, size=size)
        dst = tmp_path / f"{name}_out.mp4"
        make_vertical(src, dst, "blur", 2.0)
        assert video_size(dst) == (1080, 1920)


@needs_ffmpeg
def test_corrupt_input_reports_a_coded_error_and_leaves_no_file(tmp_path):
    src = tmp_path / "broken.mp4"
    src.write_bytes(b"this is not a video")
    dst = tmp_path / "out.mp4"
    with pytest.raises(ClipError) as err:
        make_vertical(src, dst, "blur", 3.0)
    assert err.value.code == "clip_convert_failed"
    assert not dst.exists()


@needs_ffmpeg
def test_cancel_stops_conversion_and_removes_partial_output(tmp_path):
    src = make_source(tmp_path / "src.mp4", seconds=6)
    dst = tmp_path / "out.mp4"
    with pytest.raises(ClipCancelled):
        make_vertical(src, dst, "blur", 6.0, is_cancelled=lambda: True)


# --- whole job with a fake downloader ---------------------------------------------
@needs_ffmpeg
def test_make_clip_runs_both_steps_and_reports_growing_progress(tmp_path):
    calls: list[tuple[float, float]] = []

    def fake_download(url, start, end, dest, progress, cancelled):
        calls.append((start, end))
        if progress:
            progress(0.5)
            progress(1.0)
        return make_source(dest / "section.mp4", seconds=2)

    seen: list[float] = []
    req = ClipRequest("https://youtu.be/x", "Тест", 1, 30.0, 32.0, tmp_path / "out", "blur", 600)
    result = make_clip(req, seen.append, downloader=fake_download)
    assert result.parent == tmp_path / "out" and result.exists()
    assert video_size(result) == (1080, 1920)
    assert calls == [(29.6, 32.6)]
    assert seen == sorted(seen) and seen[-1] == 1.0 and max(seen[:2]) <= clipper.DOWNLOAD_SHARE


@needs_ffmpeg
def test_make_clip_cancel_during_convert_removes_target(tmp_path):
    def fake_download(url, start, end, dest, progress, cancelled):
        return make_source(dest / "section.mp4", seconds=2)

    req = ClipRequest("u", "Тест", 1, 1.0, 3.0, tmp_path)
    with pytest.raises(ClipCancelled):
        make_clip(req, is_cancelled=lambda: True, downloader=fake_download)
    assert list(tmp_path.glob("*.mp4")) == []


def test_download_errors_pass_through(tmp_path):
    def failing(*_args):
        raise ClipError("clip_download_failed")

    with pytest.raises(ClipError) as err:
        make_clip(ClipRequest("u", "t", 1, 1, 5, tmp_path), downloader=failing)
    assert err.value.code == "clip_download_failed"


def test_unwritable_folder_is_reported(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(ClipError) as err:
        make_clip(ClipRequest("u", "t", 1, 1, 5, blocker / "sub"))
    assert err.value.code == "clip_folder"
