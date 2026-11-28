"""Cut a moment out of a YouTube video and turn it into a vertical 9:16 Short.

Two steps, both replaceable in tests:
1. download only the needed time range with yt-dlp (no full download);
2. re-encode that range to 1080x1920 with ffmpeg.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from youtube_factory.services import tools
from youtube_factory.services.exporter import safe_filename

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 1080, 1920
LEAD_IN_S = 0.4  # start a little before the first word
TAIL_S = 0.6  # and end a little after the last one
STYLES = ("blur", "crop", "fit")
DEFAULT_STYLE = "blur"
DOWNLOAD_SHARE = 0.7  # part of the progress bar used by the download step

Progress = Callable[[float], None]
Cancelled = Callable[[], bool]


class ClipError(RuntimeError):
    """A clip could not be made. `code` is a stable key for the user-facing message."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ClipCancelled(Exception):
    """The user cancelled while a clip was being made."""


@dataclass(frozen=True, slots=True)
class ClipRequest:
    url: str
    title: str
    index: int
    start_sec: float
    end_sec: float
    out_dir: Path
    style: str = DEFAULT_STYLE
    video_duration: float = 0.0


# --- helpers ---------------------------------------------------------------
def ffmpeg_path() -> str:
    """Our downloaded ffmpeg, one on PATH, or the one bundled with imageio-ffmpeg."""
    found = tools.find_tool("ffmpeg")
    if found is None:
        raise ClipError("ffmpeg_missing")
    return str(found)


def ytdlp_tool_options() -> dict:
    """yt-dlp options pointing at our ffmpeg and Deno (needed for full YouTube support)."""
    options: dict = {}
    ffmpeg = tools.find_tool("ffmpeg")
    if ffmpeg:
        options["ffmpeg_location"] = str(ffmpeg)
    deno = tools.find_tool("deno")
    if deno:
        options["js_runtimes"] = {"deno": {"path": str(deno)}}
    return options


def padded_range(start: float, end: float, duration: float = 0.0) -> tuple[float, float]:
    """Widen the range slightly and keep it inside the video."""
    start = max(0.0, start - LEAD_IN_S)
    end = end + TAIL_S
    if duration > 0:
        end = min(end, duration)
    return start, max(end, start + 1.0)


def clip_path(req: ClipRequest) -> Path:
    """Output file name: <title>_<NN>_<start>-<end>.mp4, never overwriting an existing file."""
    base = f"{safe_filename(req.title, 50)}_{req.index:02d}_{int(req.start_sec)}-{int(req.end_sec)}"
    path = req.out_dir / f"{base}.mp4"
    n = 2
    while path.exists():
        path = req.out_dir / f"{base}_{n}.mp4"
        n += 1
    return path


def vertical_filter(style: str) -> str:
    """ffmpeg -vf chain producing a 1080x1920 frame."""
    if style == "crop":  # fill the frame, cutting the sides
        return f"scale=-2:{HEIGHT},crop={WIDTH}:{HEIGHT},setsar=1"
    if style == "fit":  # whole frame on black
        return f"scale={WIDTH}:-2,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    # blur: whole frame over a blurred copy of itself. The blur runs at 1/4 size, which is
    # much cheaper and looks the same once scaled back up.
    small_w, small_h = WIDTH // 4, HEIGHT // 4
    return (
        "split=2[bg][fg];"
        f"[bg]scale={small_w}:{small_h}:force_original_aspect_ratio=increase,"
        f"crop={small_w}:{small_h},boxblur=8:2,scale={WIDTH}:{HEIGHT}[blurred];"
        f"[fg]scale={WIDTH}:-2[sharp];"
        "[blurred][sharp]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


def _popen_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


# --- step 2: vertical conversion --------------------------------------------
def make_vertical(
    src: Path,
    dst: Path,
    style: str,
    length_sec: float,
    progress: Progress | None = None,
    is_cancelled: Cancelled | None = None,
) -> None:
    """Re-encode `src` to a 1080x1920 H.264/AAC mp4 at `dst`."""
    if style not in STYLES:
        style = DEFAULT_STYLE
    cmd = [
        ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
        "-progress", "pipe:1", "-nostats",
        "-i", str(src),
        "-vf", vertical_filter(style),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-movflags", "+faststart",
        str(dst),
    ]  # fmt: skip
    with tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.Popen(  # noqa: S603 - fixed argument list, no shell
                cmd,
                stdout=subprocess.PIPE,
                stderr=err,
                text=True,
                creationflags=_popen_flags(),
            )
        except OSError as exc:
            raise ClipError("ffmpeg_missing") from exc
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                if is_cancelled and is_cancelled():
                    proc.kill()
                    raise ClipCancelled
                key, _, value = line.strip().partition("=")
                if (
                    progress
                    and key in {"out_time_us", "out_time_ms"}
                    and value.lstrip("-").isdigit()
                ):
                    done = int(value) / 1_000_000
                    progress(min(1.0, max(0.0, done / max(length_sec, 0.1))))
        finally:
            proc.stdout.close()
            code = proc.wait()
        if code != 0:
            err.seek(0)
            log.error("ffmpeg failed (%s): %s", code, err.read().decode("utf-8", "replace")[-800:])
            dst.unlink(missing_ok=True)
            raise ClipError("clip_convert_failed")
    if progress:
        progress(1.0)


# --- step 1: download a section ------------------------------------------------
def download_section(
    url: str,
    start: float,
    end: float,
    dest_dir: Path,
    progress: Progress | None = None,
    is_cancelled: Cancelled | None = None,
) -> Path:
    """Download only [start, end] of the video. Returns the downloaded file."""
    import yt_dlp
    from yt_dlp.utils import DownloadCancelled, download_range_func

    def hook(data: dict) -> None:
        if is_cancelled and is_cancelled():
            raise DownloadCancelled
        if progress and data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if total:
                progress(min(1.0, data.get("downloaded_bytes", 0) / total))

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(dest_dir / "section.%(ext)s"),
        "download_ranges": download_range_func(None, [(start, end)]),
        "force_keyframes_at_cuts": True,  # exact cut points instead of the nearest keyframe
        "progress_hooks": [hook],
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 4,
        **ytdlp_tool_options(),
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except DownloadCancelled as exc:
        raise ClipCancelled from exc
    except ClipCancelled:
        raise
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises several unrelated types
        from youtube_factory.integrations.youtube import classify_error

        log.warning("Section download failed: %s", exc)
        code = classify_error(str(exc))
        raise ClipError(code if code != "net_error" else "clip_download_failed") from exc
    files = [
        f
        for f in dest_dir.glob("section.*")
        if f.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
    ]
    if not files:
        raise ClipError("clip_download_failed")
    return max(files, key=lambda f: f.stat().st_size)


# --- whole job ---------------------------------------------------------------------
Downloader = Callable[[str, float, float, Path, Progress | None, Cancelled | None], Path]
Converter = Callable[[Path, Path, str, float, Progress | None, Cancelled | None], None]


def make_clip(
    req: ClipRequest,
    progress: Progress | None = None,
    is_cancelled: Cancelled | None = None,
    downloader: Downloader = download_section,
    converter: Converter = make_vertical,
) -> Path:
    """Download the moment and convert it. Returns the finished file."""
    try:
        req.out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ClipError("clip_folder") from exc
    start, end = padded_range(req.start_sec, req.end_sec, req.video_duration)
    target = clip_path(req)

    def report(share_from: float, share_to: float) -> Progress:
        def inner(fraction: float) -> None:
            if progress:
                progress(share_from + (share_to - share_from) * fraction)

        return inner

    with tempfile.TemporaryDirectory(prefix="yf-clip-", ignore_cleanup_errors=True) as tmp:
        section = downloader(
            req.url, start, end, Path(tmp), report(0.0, DOWNLOAD_SHARE), is_cancelled
        )
        try:
            converter(
                section, target, req.style, end - start,
                report(DOWNLOAD_SHARE, 1.0), is_cancelled,
            )  # fmt: skip
        except ClipCancelled:
            target.unlink(missing_ok=True)
            raise
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise ClipError("clip_folder") from exc
    return target
