"""User settings stored as JSON in the user data directory.

Secrets (API keys) are never stored here. They come from environment
variables or a local ``.env`` file, see ``env.py``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

THEMES = ("dark", "light", "system")


@dataclass(slots=True)
class Settings:
    theme: str = "dark"
    export_dir: str = ""
    window_width: int = 1200
    window_height: int = 800

    def normalized(self) -> Settings:
        if self.theme not in THEMES:
            self.theme = "dark"
        self.window_width = max(900, min(7680, int(self.window_width)))
        self.window_height = max(600, min(4320, int(self.window_height)))
        return self


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> Settings:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            known = {k: v for k, v in raw.items() if k in Settings.__dataclass_fields__}
            return Settings(**known).normalized()
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError, TypeError):
            log.warning("Settings file is unreadable, using defaults", exc_info=True)
            return Settings()

    def save(self, settings: Settings) -> None:
        """Write atomically so a crash cannot leave a half-written file."""
        settings.normalized()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, self._path)
