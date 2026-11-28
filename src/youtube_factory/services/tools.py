"""Helper programs the app needs for clips: ffmpeg (video) and Deno (YouTube's JavaScript).

They are large (about 100 MB each unpacked), so they are not baked into the exe. On
Windows they are downloaded once, on first use, into the app data folder. The files come
from PyPI wheels pinned by version and SHA-256, so a changed or damaged download is
rejected. On other systems the tools must already be installed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from youtube_factory.data.paths import data_dir

log = logging.getLogger(__name__)

CHUNK = 256 * 1024
NET_TIMEOUT_S = 30
USER_AGENT = "YouTubeFactory tool installer"


class ToolsError(RuntimeError):
    """Tools could not be installed. `code` is a stable key for the user-facing message."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ToolsCancelled(Exception):
    """The user cancelled while tools were being downloaded."""


@dataclass(frozen=True, slots=True)
class Tool:
    key: str  # "ffmpeg" or "deno"
    title: str
    package: str  # PyPI package whose Windows wheel contains the program
    version: str
    sha256: str  # of the wheel file
    member: str  # path of the program inside the wheel
    filename: str  # name on disk


TOOLS: dict[str, Tool] = {
    "ffmpeg": Tool(
        "ffmpeg",
        "ffmpeg",
        "imageio-ffmpeg",
        "0.8.2",
        "c5d528e1daa9c17c71d7a600c31e1a0983ca739a20dd014159b2b7431b0b1ea7",
        "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v9.0.2.exe",
        "ffmpeg.exe",
    ),
    "deno": Tool(
        "deno",
        "Deno",
        "deno",
        "2.9.8",
        "60dd97e612b8bab67c8080712646a821071e3809909489f853763cea19617700",
        "deno-2.9.8.data/scripts/deno.exe",
        "deno.exe",
    ),
}

ToolProgress = Callable[[str, float], None]  # tool title, 0..1
OpenUrl = Callable[[str], BinaryIO]


def tools_dir() -> Path:
    return data_dir() / "tools"


def _is_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def find_tool(key: str) -> Path | None:
    """Our downloaded copy first, then the system PATH, then (for ffmpeg) imageio-ffmpeg."""
    tool = TOOLS[key]
    own = tools_dir() / tool.filename
    if _is_file(own):
        return own
    found = shutil.which(key)
    if found:
        return Path(found)
    if key == "ffmpeg":
        try:
            import imageio_ffmpeg

            exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
            if _is_file(exe):
                return exe
        except Exception:  # noqa: BLE001 - optional source
            log.debug("imageio-ffmpeg is not usable", exc_info=True)
    return None


def missing_tools() -> list[Tool]:
    return [t for key, t in TOOLS.items() if find_tool(key) is None]


def can_install_here() -> bool:
    return sys.platform == "win32"


def _default_open(url: str) -> BinaryIO:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=NET_TIMEOUT_S)  # noqa: S310


def _wheel_url(tool: Tool, open_url: OpenUrl) -> str:
    meta_url = f"https://pypi.org/pypi/{tool.package}/{tool.version}/json"
    with open_url(meta_url) as response:
        meta = json.load(response)
    for item in meta.get("urls", []):
        if str(item.get("filename", "")).endswith("win_amd64.whl"):
            return str(item["url"])
    raise ToolsError("tools_download_failed")


def install_tool(
    tool: Tool,
    target_dir: Path,
    progress: ToolProgress | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    open_url: OpenUrl = _default_open,
) -> Path:
    """Download the tool's wheel, check its hash and unpack the program."""
    target_dir.mkdir(parents=True, exist_ok=True)
    final = target_dir / tool.filename
    try:
        url = _wheel_url(tool, open_url)
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=target_dir, suffix=".part", delete=False) as part:
            part_path = Path(part.name)
            with open_url(url) as response:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                while chunk := response.read(CHUNK):
                    if is_cancelled and is_cancelled():
                        raise ToolsCancelled
                    part.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress and total:
                        progress(tool.title, min(0.95, done / total))
        if digest.hexdigest() != tool.sha256:
            log.error("Hash mismatch for %s: %s", tool.key, digest.hexdigest())
            raise ToolsError("tools_corrupt")
        with zipfile.ZipFile(part_path) as wheel, wheel.open(tool.member) as src:
            staging = target_dir / (tool.filename + ".new")
            with open(staging, "wb") as out:
                shutil.copyfileobj(src, out, CHUNK)
        os.replace(staging, final)
    except ToolsError:
        raise
    except ToolsCancelled:
        raise
    except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        log.warning("Could not install %s: %s", tool.key, exc)
        raise ToolsError("tools_download_failed") from exc
    finally:
        for leftover in target_dir.glob("*.part"):
            leftover.unlink(missing_ok=True)
        (target_dir / (tool.filename + ".new")).unlink(missing_ok=True)
    if progress:
        progress(tool.title, 1.0)
    return final


def ensure_tools(
    progress: ToolProgress | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    open_url: OpenUrl = _default_open,
    target_dir: Path | None = None,
) -> None:
    """Make sure every tool exists, downloading missing ones (Windows only)."""
    missing = missing_tools()
    if not missing:
        return
    if not can_install_here():
        raise ToolsError("tools_missing")
    for tool in missing:
        install_tool(tool, target_dir or tools_dir(), progress, is_cancelled, open_url)
