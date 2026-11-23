"""Fail if the protected repository file was changed, renamed or removed.

Usage: python scripts/verify_protected_file.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROTECTED_NAME = "pogoda-widget@example.com.zip"
EXPECTED_SHA256 = "a2c8260fceb7ca8aa5b4dfe6e3880461d493e833ecfc29114b6a2d453cebc607"
EXPECTED_SIZE = 118148


def main() -> int:
    path = Path(__file__).resolve().parent.parent / PROTECTED_NAME
    if not path.is_file():
        print(f"ERROR: protected file is missing: {PROTECTED_NAME}")
        return 1
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        print(f"ERROR: protected file was modified: {PROTECTED_NAME}")
        print(f"  size={len(data)} sha256={digest}")
        return 1
    print(f"OK: {PROTECTED_NAME} is present and unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
