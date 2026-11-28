"""Text helpers shared by all screens."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from youtube_factory.ui.fonts import font

# role -> (pixel size, weight)
ROLES: dict[str, tuple[int, str]] = {
    "hero": (36, "bold"),
    "title": (26, "semibold"),
    "h2": (18, "semibold"),
    "h3": (15, "medium"),
    "body": (14, "regular"),
    "muted": (14, "regular"),
    "small": (12, "regular"),
    "error": (14, "medium"),
    "accent": (14, "medium"),
}


def make_label(text: str = "", wrap: bool = False, role: str = "body") -> QLabel:
    label = QLabel(text)
    label.setWordWrap(wrap)
    px, weight = ROLES[role]
    f = font(px, weight)
    if role == "hero":
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
    label.setFont(f)
    label.setProperty("role", role)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    return label


def set_paragraph(label: QLabel, text: str, line_height: int = 138) -> None:
    """Show wrapped text with a calmer line height than the font default."""
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(f'<p style="line-height:{line_height}%; margin:0">{html.escape(text)}</p>')


def transparent_scroll(host: QWidget) -> QScrollArea:
    """Scroll area that lets the window backdrop show through."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(host)
    # QScrollArea.setWidget turns auto-fill back on, so these must come after it.
    scroll.viewport().setAutoFillBackground(False)
    host.setAutoFillBackground(False)
    return scroll
