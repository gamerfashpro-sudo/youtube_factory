"""Application entry point."""

from __future__ import annotations

import logging
import sys

from youtube_factory import __version__
from youtube_factory.data.logging_setup import setup_logging

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    setup_logging()
    log.info("Starting YouTube Factory %s", __version__)
    if "--version" in args:
        print(__version__)
        return 0
    # The Qt application is wired up in a later stage.
    log.warning("UI is not implemented yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
