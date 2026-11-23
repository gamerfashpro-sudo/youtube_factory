"""Small helpers for building widgets that the stylesheet can target."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QPushButton


def make_label(text: str = "", wrap: bool = False, **props: bool) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(wrap)
    for key, value in props.items():
        label.setProperty(key, value)
    return label


def make_button(text: str, tooltip: str = "", **props: bool) -> QPushButton:
    button = QPushButton(text)
    if tooltip:
        button.setToolTip(tooltip)
    for key, value in props.items():
        button.setProperty(key, value)
    return button


def make_card() -> QFrame:
    frame = QFrame()
    frame.setProperty("card", True)
    return frame


def set_prop(widget, name: str, value: bool) -> None:
    """Change a dynamic property and re-apply the stylesheet."""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
