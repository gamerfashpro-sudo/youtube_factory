"""Application entry point."""

from __future__ import annotations

import sys

from youtube_factory import __version__


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--version" in args:
        print(__version__)
        return 0
    from youtube_factory.app.bootstrap import run

    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
