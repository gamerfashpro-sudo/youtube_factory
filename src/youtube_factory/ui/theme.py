"""Design tokens: palettes, radii and the small global stylesheet.

The look is built from a pre-rendered blurred backdrop and translucent "glass"
panels painted with plain gradients. There is no real-time blur or drop shadow,
so the interface stays cheap to repaint.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

# Radii: larger surfaces are rounder, small controls are tighter.
R_DOCK = 26
R_PANEL = 20
R_FIELD = 14
R_CONTROL = 12


def rgba(hex_: str, alpha: int = 255) -> QColor:
    c = QColor(hex_)
    c.setAlpha(alpha)
    return c


@dataclass(frozen=True)
class Blob:
    x: float  # centre as a fraction of window width
    y: float  # centre as a fraction of window height
    r: float  # radius as a fraction of the larger window side
    color: str
    alpha: int


@dataclass(frozen=True, eq=False)
class Palette:
    name: str
    dark: bool
    base: QColor
    blobs: tuple[Blob, ...]
    glass_a: QColor  # fill at the top of a panel
    glass_b: QColor  # fill at the bottom of a panel
    stroke_hi: QColor  # lit edge (top left)
    stroke_lo: QColor  # shaded edge (bottom right)
    text: QColor
    muted: QColor
    faint: QColor
    accent: QColor
    accent_hi: QColor
    accent_lo: QColor
    on_accent: QColor
    amber: QColor
    danger: QColor
    success: QColor
    field: QColor
    track: QColor


DARK = Palette(
    name="dark",
    dark=True,
    base=rgba("#0A0A0C"),
    blobs=(
        Blob(0.10, 0.04, 0.62, "#7C5CFF", 120),
        Blob(0.96, 0.12, 0.52, "#3552FF", 66),
        Blob(0.86, 1.00, 0.62, "#FF8A3D", 44),
        Blob(0.00, 1.00, 0.48, "#B03CFF", 42),
    ),
    glass_a=rgba("#FFFFFF", 24),
    glass_b=rgba("#FFFFFF", 10),
    stroke_hi=rgba("#FFFFFF", 92),
    stroke_lo=rgba("#FFFFFF", 16),
    text=rgba("#F5F5F9"),
    muted=rgba("#A9A9BC"),
    faint=rgba("#7C7C90"),
    accent=rgba("#7C5CFF"),
    accent_hi=rgba("#9A82FF"),
    accent_lo=rgba("#6040F0"),
    on_accent=rgba("#FFFFFF"),
    amber=rgba("#FFB020"),
    danger=rgba("#FF7083"),
    success=rgba("#4ADE9A"),
    field=rgba("#000000", 78),
    track=rgba("#FFFFFF", 28),
)

LIGHT = Palette(
    name="light",
    dark=False,
    base=rgba("#EDECF6"),
    blobs=(
        Blob(0.08, 0.04, 0.65, "#9D88FF", 140),
        Blob(0.96, 0.14, 0.55, "#7DB5FF", 120),
        Blob(0.86, 1.00, 0.65, "#FFB47E", 120),
    ),
    glass_a=rgba("#FFFFFF", 176),
    glass_b=rgba("#FFFFFF", 112),
    stroke_hi=rgba("#FFFFFF", 240),
    stroke_lo=rgba("#1E1B3A", 40),
    text=rgba("#17161F"),
    muted=rgba("#5A5870"),
    faint=rgba("#8C8AA0"),
    accent=rgba("#6A4BF0"),
    accent_hi=rgba("#7D62F5"),
    accent_lo=rgba("#5A3BE0"),
    on_accent=rgba("#FFFFFF"),
    amber=rgba("#D98200"),
    danger=rgba("#D93646"),
    success=rgba("#1E9E6A"),
    field=rgba("#FFFFFF", 150),
    track=rgba("#1E1B3A", 34),
)


def _css(c: QColor) -> str:
    return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"


def build_stylesheet(p: Palette) -> str:
    handle = QColor(p.text)
    handle.setAlpha(60)
    return f"""
QToolTip {{
    background: {_css(rgba("#1B1B22") if p.dark else rgba("#FFFFFF"))};
    color: {_css(p.text)}; border: 1px solid {_css(p.stroke_lo)};
    border-radius: 8px; padding: 6px 10px;
}}
QLabel {{ background: transparent; color: {_css(p.text)}; }}
QLabel[role="muted"], QLabel[role="small"] {{ color: {_css(p.muted)}; }}
QLabel[role="error"] {{ color: {_css(p.danger)}; }}
QLabel[role="accent"] {{ color: {_css(p.accent_hi)}; }}
QLineEdit, QPlainTextEdit {{
    background: transparent; border: none; color: {_css(p.text)};
    selection-background-color: {_css(p.accent)}; selection-color: white;
}}
QLineEdit:disabled {{ color: {_css(p.faint)}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {_css(handle)}; border-radius: 3px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: {_css(p.muted)}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""


class ThemeManager(QObject):
    """Holds the active palette and tells widgets when it changes."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.p: Palette = DARK
        self._choice = "dark"

    def set_choice(self, choice: str) -> None:
        self._choice = choice if choice in ("dark", "light", "system") else "dark"
        self.refresh()

    def _resolve(self) -> Palette:
        if self._choice == "light":
            return LIGHT
        if self._choice == "system":
            scheme = QApplication.styleHints().colorScheme()
            return LIGHT if scheme == Qt.ColorScheme.Light else DARK
        return DARK

    def refresh(self) -> None:
        new = self._resolve()
        first = QApplication.instance().styleSheet() == ""
        if new is not self.p or first:
            self.p = new
            QApplication.instance().setStyleSheet(build_stylesheet(new))
            self.changed.emit()

    def watch_system(self) -> None:
        QApplication.styleHints().colorSchemeChanged.connect(
            lambda *_: self.refresh() if self._choice == "system" else None
        )


theme = ThemeManager()
