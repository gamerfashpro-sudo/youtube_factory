"""Locations of per-user data. Nothing is stored in the installation folder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_data_dir

from youtube_factory import APP_NAME


def data_dir() -> Path:
    """Return the per-user data directory, creating it if needed."""
    override = os.environ.get("YOUTUBE_FACTORY_DATA_DIR")
    path = Path(override) if override else Path(user_data_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "history.sqlite3"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def log_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_dir() -> Path:
    """Folder with bundled resources (icon, fonts) in a checkout or a PyInstaller bundle."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "youtube_factory" / "resources"
    return Path(__file__).resolve().parents[1] / "resources"


def long_path(path: Path) -> str:
    """Return a path string safe for Windows paths longer than 260 characters."""
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        if resolved.startswith("\\\\"):
            return "\\\\?\\UNC\\" + resolved[2:]
        return "\\\\?\\" + resolved
    return resolved


def default_clips_dir() -> Path:
    """Where finished Shorts go unless the user picked another folder."""
    videos = Path.home() / "Videos"
    return (videos if videos.is_dir() else Path.home()) / "YouTube Factory"
