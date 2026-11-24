"""PyInstaller entry point. Kept outside the package so imports stay absolute."""

from youtube_factory.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
