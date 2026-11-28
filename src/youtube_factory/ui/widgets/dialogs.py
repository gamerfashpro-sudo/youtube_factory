"""Dialogs that match the glass look: shared base, confirmation and transcript input."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.workers import error_code, error_message
from youtube_factory.models import TranscriptSegment
from youtube_factory.services.transcript_parser import (
    TranscriptError,
    parse_transcript,
    read_transcript_file,
)
from youtube_factory.ui import winfx
from youtube_factory.ui.backdrop import paint_backdrop
from youtube_factory.ui.theme import theme
from youtube_factory.ui.widgets.common import make_label, set_paragraph
from youtube_factory.ui.widgets.controls import GlassButton
from youtube_factory.ui.widgets.fields import GlassLineEdit, GlassTextEdit
from youtube_factory.ui.widgets.glass import GlassPanel


class GlassDialog(QDialog):
    """Dialog that paints the same backdrop as the main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        theme.changed.connect(self.update)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        winfx.style_title_bar(self, theme.p.dark, theme.p.base, theme.p.text)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        paint_backdrop(p, event.rect(), self.size(), theme.p)


def confirm(parent: QWidget, title: str, text: str, action: str = "") -> bool:
    """Ask for confirmation of a destructive action. True when the user accepts."""
    dlg = GlassDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedWidth(460)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(20, 20, 20, 20)
    panel = GlassPanel()
    inner = QVBoxLayout(panel)
    inner.setContentsMargins(26, 24, 26, 22)
    inner.setSpacing(10)
    inner.addWidget(make_label(title, role="h2"))
    body = make_label(wrap=True, role="muted")
    set_paragraph(body, text)
    inner.addWidget(body)
    inner.addSpacing(10)
    row = QHBoxLayout()
    row.addStretch(1)
    cancel = GlassButton(ru.BTN_CANCEL, "secondary")
    yes = GlassButton(action or ru.BTN_DELETE, "danger", "trash")
    row.addWidget(cancel)
    row.addWidget(yes)
    inner.addLayout(row)
    lay.addWidget(panel)
    cancel.clicked.connect(dlg.reject)
    yes.clicked.connect(dlg.accept)
    cancel.setFocus()
    return dlg.exec() == QDialog.DialogCode.Accepted


class TranscriptDialog(GlassDialog):
    def __init__(self, parent: QWidget | None = None, start_dir: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(ru.TRANSCRIPT_DIALOG_TITLE)
        self.setMinimumSize(680, 560)
        self._start_dir = start_dir
        self.segments: list[TranscriptSegment] = []
        self.timed = False
        self.video_title = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        panel = GlassPanel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(12)
        layout.addWidget(make_label(ru.TRANSCRIPT_DIALOG_TITLE, role="h2"))
        layout.addWidget(make_label(ru.TRANSCRIPT_HINT, role="muted"))
        self.title_edit = GlassLineEdit(ru.TITLE_OPTIONAL_PLACEHOLDER, "film")
        layout.addWidget(self.title_edit)
        self.text_edit = GlassTextEdit(ru.TRANSCRIPT_PLACEHOLDER)
        layout.addWidget(self.text_edit, 1)
        self.error_label = make_label(wrap=True, role="error")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        self.open_btn = GlassButton(ru.BTN_OPEN_FILE, "secondary", "folder")
        self.ok_btn = GlassButton(ru.BTN_ANALYZE, "primary", "sparkle")
        self.cancel_btn = GlassButton(ru.BTN_CANCEL, "ghost")
        buttons.addWidget(self.open_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)
        outer.addWidget(panel)

        self.open_btn.clicked.connect(self._open_file)
        self.ok_btn.clicked.connect(self._accept)
        self.cancel_btn.clicked.connect(self.reject)

    def _show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.show()

    def _open_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, ru.OPEN_FILE_TITLE, self._start_dir, ru.FILE_FILTER
        )
        if not name:
            return
        try:
            segments, timed = read_transcript_file(Path(name))
        except TranscriptError as exc:
            self._show_error(error_message(error_code(exc)))
            return
        self.error_label.hide()
        self.segments, self.timed = segments, timed
        self.text_edit.setPlainText("\n".join(s.text for s in segments))
        if not self.title_edit.text().strip():
            self.title_edit.setText(Path(name).stem)

    def _accept(self) -> None:
        # Re-parse pasted text unless it came unchanged from a file with timestamps.
        text = self.text_edit.toPlainText()
        if not (self.segments and self.timed and text == "\n".join(s.text for s in self.segments)):
            try:
                self.segments, self.timed = parse_transcript(text)
            except TranscriptError as exc:
                self._show_error(error_message(error_code(exc)))
                return
        self.video_title = self.title_edit.text().strip()
        self.accept()
