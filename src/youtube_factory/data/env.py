"""Read secrets from the environment or a local .env file. Never hardcode keys."""

from __future__ import annotations

import os
from pathlib import Path

KNOWN_KEYS = (
    "YOUTUBE_API_KEY",
    "TRANSCRIPT_PROVIDER",
    "TRANSCRIPT_API_KEY",
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def get_secret(name: str, env_file: Path | None = None) -> str | None:
    """Environment variables win over the .env file. Empty values count as unset."""
    value = os.environ.get(name)
    if value:
        return value
    if env_file is not None:
        return parse_env_file(env_file).get(name) or None
    return None
