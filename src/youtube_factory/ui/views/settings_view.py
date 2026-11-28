"""Settings screen: appearance, files, future integrations and About, each on its own shelf."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import __version__
from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.data.paths import data_dir, default_clips_dir
from youtube_factory.ui.motion import motion
from youtube_factory.ui.widgets.common import make_label, set_paragraph, transparent_scroll
from youtube_factory.ui.widgets.controls import GlassButton, Segmented, Switch
from youtube_factory.ui.widgets.fields import GlassLineEdit
from youtube_factory.ui.widgets.glass import GlassPanel

THEME_ITEMS = (
    ("dark", ru.THEME_DARK),
    ("light", ru.THEME_LIGHT),
    ("system", ru.THEME_SYSTEM),
)
CONTENT_MAX = 760


class Shelf(GlassPanel):
    """A titled glass panel; rows are added to `body`."""

    def __init__(self, title: str) -> None:
        super().__init__(radius=20)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 22)
        lay.setSpacing(14)
        lay.addWidget(make_label(title, role="h2"))
        self.body = QVBoxLayout()
        self.body.setSpacing(16)
        lay.addLayout(self.body)

    def add_row(self, title: str, control: QWidget, hint: str = "") -> None:
        row = QHBoxLayout()
        row.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(make_label(title, role="h3"))
        if hint:
            text.addWidget(make_label(hint, wrap=True, role="small"))
        row.addLayout(text, 1)
        row.addWidget(control)
        self.body.addLayout(row)


class SettingsView(QWidget):
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        host = QWidget()
        page = QHBoxLayout(host)
        page.setContentsMargins(36, 40, 36, 32)
        column = QWidget()
        column.setMaximumWidth(CONTENT_MAX)
        page.addWidget(column, 1)
        page.addStretch(0)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(make_label(ru.SETTINGS_TITLE, role="title"))
        layout.addSpacing(4)

        look = Shelf(ru.SETTINGS_APPEARANCE)
        self.theme_combo = Segmented()
        for key, title in THEME_ITEMS:
            self.theme_combo.addItem(title, key)
        look.add_row(ru.SETTINGS_THEME, self.theme_combo)
        self.anim_switch = Switch()
        look.add_row(ru.SETTINGS_ANIMATIONS, self.anim_switch, ru.SETTINGS_ANIMATIONS_HINT)
        layout.addWidget(look)

        clips = Shelf(ru.SETTINGS_CLIPS)
        self.style_combo = Segmented()
        for key, title in (
            ("blur", ru.CLIP_STYLE_BLUR),
            ("crop", ru.CLIP_STYLE_CROP),
            ("fit", ru.CLIP_STYLE_FIT),
        ):
            self.style_combo.addItem(title, key)
        clips.add_row(ru.SETTINGS_CLIP_STYLE, self.style_combo, ru.SETTINGS_CLIP_STYLE_HINT)
        self.clips_dir_edit = GlassLineEdit(ru.EXPORT_DIR_PLACEHOLDER, "folder", height=42)
        self.clips_dir_edit.setReadOnly(True)
        self.clips_dir_btn = GlassButton(ru.BTN_CHOOSE_FOLDER, "secondary")
        clips.body.addWidget(make_label(ru.SETTINGS_CLIPS_DIR, role="h3"))
        clips_pick = QHBoxLayout()
        clips_pick.setSpacing(8)
        clips_pick.addWidget(self.clips_dir_edit, 1)
        clips_pick.addWidget(self.clips_dir_btn)
        clips.body.addLayout(clips_pick)
        layout.addWidget(clips)

        files = Shelf(ru.SETTINGS_FILES)
        self.dir_edit = GlassLineEdit(ru.EXPORT_DIR_PLACEHOLDER, "folder", height=42)
        self.dir_edit.setReadOnly(True)
        self.dir_btn = GlassButton(ru.BTN_CHOOSE_FOLDER, "secondary")
        files.body.addWidget(make_label(ru.SETTINGS_EXPORT_DIR, role="h3"))
        pick = QHBoxLayout()
        pick.setSpacing(8)
        pick.addWidget(self.dir_edit, 1)
        pick.addWidget(self.dir_btn)
        files.body.addLayout(pick)
        layout.addWidget(files)

        api = Shelf(ru.SETTINGS_API_TITLE)
        note = make_label(wrap=True, role="muted")
        set_paragraph(note, ru.SETTINGS_API_NOTE)
        api.body.addWidget(note)
        for caption in (ru.API_YOUTUBE, ru.API_TRANSCRIPTS, ru.API_LLM):
            field = GlassLineEdit(ru.API_SOON, None, height=42)
            field.setEnabled(False)
            api.body.addWidget(make_label(caption, role="h3"))
            api.body.addWidget(field)
        layout.addWidget(api)

        about = Shelf(ru.SETTINGS_ABOUT)
        name_line, version_line, privacy_line = ru.ABOUT_TEXT.format(
            name=ru.APP_TITLE, version=__version__
        ).split("\n")
        about.body.addWidget(make_label(f"{name_line}, {version_line.lower()}", role="h3"))
        about.body.addWidget(make_label(privacy_line, wrap=True, role="muted"))
        self.data_btn = GlassButton(ru.BTN_OPEN_DATA_DIR, "secondary", "folder")
        row = QHBoxLayout()
        row.addWidget(self.data_btn)
        row.addStretch(1)
        about.body.addLayout(row)
        layout.addWidget(about)
        layout.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(transparent_scroll(host))

        self.load_from_settings()
        self.theme_combo.currentChanged.connect(self._theme_changed)
        self.anim_switch.toggled.connect(self._animations_changed)
        self.dir_btn.clicked.connect(self._choose_dir)
        self.style_combo.currentChanged.connect(self._style_changed)
        self.clips_dir_btn.clicked.connect(self._choose_clips_dir)
        self.data_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))
        )

    def load_from_settings(self) -> None:
        s = self._controller.settings
        self.theme_combo.blockSignals(True)
        self.theme_combo.set_index_silently(max(0, self.theme_combo.findData(s.theme)))
        self.theme_combo.blockSignals(False)
        self.anim_switch.blockSignals(True)
        self.anim_switch.setChecked(s.animations)
        self.anim_switch.blockSignals(False)
        self.dir_edit.setText(s.export_dir)
        self.style_combo.set_index_silently(max(0, self.style_combo.findData(s.clip_style)))
        self.clips_dir_edit.setText(s.clips_dir or str(default_clips_dir()))

    def _theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self._controller.update_settings(replace(self._controller.settings, theme=theme))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)

    def _animations_changed(self, on: bool) -> None:
        motion.enabled = on
        self._controller.update_settings(replace(self._controller.settings, animations=on))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)

    def _style_changed(self) -> None:
        style = self.style_combo.currentData()
        self._controller.update_settings(replace(self._controller.settings, clip_style=style))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)

    def _choose_clips_dir(self) -> None:
        start = self._controller.clips_folder()
        folder = QFileDialog.getExistingDirectory(self, ru.CHOOSE_FOLDER_TITLE, start)
        if not folder:
            return
        self.clips_dir_edit.setText(folder)
        self._controller.update_settings(replace(self._controller.settings, clips_dir=folder))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)

    def _choose_dir(self) -> None:
        start = self._controller.settings.export_dir
        folder = QFileDialog.getExistingDirectory(self, ru.CHOOSE_FOLDER_TITLE, start)
        if not folder:
            return
        self.dir_edit.setText(folder)
        self._controller.update_settings(replace(self._controller.settings, export_dir=folder))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)
