"""Colour palettes and the application stylesheet (dark, light, system)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_text: str
    score: str
    danger: str


DARK = Palette(
    bg="#0A0A0B",
    surface="#141416",
    surface_alt="#1C1C20",
    border="#2A2A30",
    text="#F2F2F4",
    text_muted="#9A9AA5",
    accent="#7C5CFF",
    accent_hover="#9179FF",
    accent_text="#FFFFFF",
    score="#FFB020",
    danger="#FF6B6B",
)

LIGHT = Palette(
    bg="#F6F6F9",
    surface="#FFFFFF",
    surface_alt="#EFEFF4",
    border="#DADAE3",
    text="#16161A",
    text_muted="#6B6B78",
    accent="#6A4BF0",
    accent_hover="#7C60F5",
    accent_text="#FFFFFF",
    score="#D98200",
    danger="#D93636",
)


def resolve_palette(theme: str) -> Palette:
    if theme == "light":
        return LIGHT
    if theme == "system":
        scheme = QApplication.styleHints().colorScheme()
        return LIGHT if scheme == Qt.ColorScheme.Light else DARK
    return DARK


def build_stylesheet(p: Palette) -> str:
    return f"""
* {{ font-family: "Segoe UI Variable", "Segoe UI", sans-serif; font-size: 10pt; }}
QMainWindow, QWidget#root, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {p.bg}; color: {p.text};
}}
QLabel {{ color: {p.text}; background: transparent; }}
QLabel[muted="true"] {{ color: {p.text_muted}; }}
QLabel[h1="true"] {{ font-size: 24pt; font-weight: 700; }}
QLabel[h2="true"] {{ font-size: 15pt; font-weight: 600; }}
QLabel[score="true"] {{ color: {p.score}; font-weight: 700; font-size: 13pt; }}
QLabel[error="true"] {{ color: {p.danger}; }}
QLabel[time="true"] {{ color: {p.accent_hover}; font-weight: 600; }}
QFrame[card="true"] {{
    background: {p.surface}; border: 1px solid {p.border}; border-radius: 14px;
}}
QFrame[nav="true"] {{ background: {p.surface}; border-right: 1px solid {p.border}; }}
QPushButton {{
    background: {p.surface_alt}; color: {p.text}; border: 1px solid {p.border};
    border-radius: 10px; padding: 8px 16px;
}}
QPushButton:hover {{ border-color: {p.accent}; }}
QPushButton:disabled {{ color: {p.text_muted}; }}
QPushButton[primary="true"] {{
    background: {p.accent}; color: {p.accent_text}; border: none; font-weight: 600;
    padding: 12px 24px;
}}
QPushButton[primary="true"]:hover {{ background: {p.accent_hover}; }}
QPushButton[nav="true"] {{
    background: transparent; border: none; text-align: left; padding: 10px 14px;
    border-radius: 10px;
}}
QPushButton[nav="true"]:checked {{ background: {p.surface_alt}; color: {p.accent_hover}; }}
QPushButton[nav="true"]:hover {{ background: {p.surface_alt}; }}
QPushButton[danger="true"] {{ color: {p.danger}; }}
QPushButton[fav="true"] {{ color: {p.score}; border-color: {p.score}; }}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{
    background: {p.surface}; color: {p.text}; border: 1px solid {p.border};
    border-radius: 10px; padding: 8px 12px; selection-background-color: {p.accent};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {p.accent};
}}
QLineEdit[big="true"] {{ font-size: 13pt; padding: 14px 18px; border-radius: 14px; }}
QComboBox QAbstractItemView {{
    background: {p.surface}; color: {p.text}; selection-background-color: {p.accent};
}}
QCheckBox {{ color: {p.text}; spacing: 8px; }}
QProgressBar {{
    background: {p.surface_alt}; border: none; border-radius: 4px; height: 8px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QDialog, QMessageBox {{ background: {p.surface}; color: {p.text}; }}
QToolTip {{ background: {p.surface_alt}; color: {p.text}; border: 1px solid {p.border}; }}
"""


def apply_theme(app: QApplication, theme: str) -> Palette:
    palette = resolve_palette(theme)
    app.setStyleSheet(build_stylesheet(palette))
    return palette
