"""Rotating file logging in the user data directory."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from youtube_factory.data.paths import log_dir

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = RotatingFileHandler(
        log_dir() / "youtube_factory.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _CONFIGURED = True
