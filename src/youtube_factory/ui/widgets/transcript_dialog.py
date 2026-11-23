"""Dialog for pasting a transcript or opening a .txt/.srt/.vtt file."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from youtube_factory import strings_ru as ru
from youtube_factory.app.workers import error_code, error_message
from youtube_factory.models import TranscriptSegment
from youtube_factory.services.transcript_parser import (
    TranscriptError,
    parse_transcript,
    read_transcript_file,
)
from youtube_factory.ui.widgets.common import make_button, make_label


class TranscriptDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, start_dir: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(ru.TRANSCRIPT_DIALOG_TITLE)
        self.setMinimumSize(640, 480)
        self._start_dir = start_dir
        self.segments: list[TranscriptSegment] = []
        self.timed = False
        self.video_title = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(make_label(ru.TRANSCRIPT_DIALOG_TITLE, h2=True))
        layout.addWidget(make_label(ru.TRANSCRIPT_HINT, muted=True))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(ru.TITLE_OPTIONAL_PLACEHOLDER)
        layout.addWidget(self.title_edit)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(ru.TRANSCRIPT_PLACEHOLDER)
        layout.addWidget(self.text_edit, 1)
        self.error_label = make_label(wrap=True, error=True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        self.open_btn = make_button(ru.BTN_OPEN_FILE)
        self.ok_btn = make_button(ru.BTN_ANALYZE, primary=True)
        self.cancel_btn = make_button(ru.BTN_CANCEL)
        buttons.addWidget(self.open_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

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
