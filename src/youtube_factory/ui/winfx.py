"""Windows 11 niceties: a title bar that matches the theme. No-op on other systems."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

log = logging.getLogger(__name__)

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colorref(c: QColor) -> int:
    return c.red() | (c.green() << 8) | (c.blue() << 16)


def style_title_bar(window: QWidget, dark: bool, caption: QColor, text: QColor) -> None:
    """Match the native title bar to the theme. Failures are ignored on purpose."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(window.winId()))
        dwm = ctypes.windll.dwmapi

        def put(attribute: int, value: int) -> None:
            v = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(v), ctypes.sizeof(v))

        put(DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)
        put(DWMWA_CAPTION_COLOR, _colorref(caption))
        put(DWMWA_TEXT_COLOR, _colorref(text))
    except Exception:  # noqa: BLE001 - purely cosmetic
        log.debug("Could not style the title bar", exc_info=True)
