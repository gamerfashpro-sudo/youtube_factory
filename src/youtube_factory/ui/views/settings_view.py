"""Settings screen: theme, export folder, future integrations and About."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_factory import __version__
from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.data.paths import data_dir
from youtube_factory.ui.widgets.common import make_button, make_card, make_label

THEME_ITEMS = (
    ("dark", ru.THEME_DARK),
    ("light", ru.THEME_LIGHT),
    ("system", ru.THEME_SYSTEM),
)


class SettingsView(QWidget):
    toast_requested = Signal(str, bool)

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)
        host = QWidget()
        scroll.setWidget(host)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(48, 40, 48, 32)
        layout.setSpacing(16)
        layout.addWidget(make_label(ru.SETTINGS_TITLE, h1=True))

        # Appearance
        layout.addWidget(make_label(ru.SETTINGS_THEME, h2=True))
        self.theme_combo = QComboBox()
        for key, title in THEME_ITEMS:
            self.theme_combo.addItem(title, key)
        self.theme_combo.setMaximumWidth(260)
        layout.addWidget(self.theme_combo)

        # Export folder
        layout.addWidget(make_label(ru.SETTINGS_EXPORT_DIR, h2=True))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setPlaceholderText(ru.EXPORT_DIR_PLACEHOLDER)
        self.dir_btn = make_button(ru.BTN_CHOOSE_FOLDER)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(self.dir_btn)
        layout.addLayout(row)

        # Future integrations (disabled placeholders)
        layout.addWidget(make_label(ru.SETTINGS_API_TITLE, h2=True))
        card = make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.addWidget(make_label(ru.SETTINGS_API_NOTE, wrap=True, muted=True))
        for caption in (ru.API_YOUTUBE, ru.API_TRANSCRIPTS, ru.API_LLM):
            card_layout.addWidget(make_label(caption))
            field = QLineEdit()
            field.setPlaceholderText(ru.API_SOON)
            field.setEnabled(False)
            card_layout.addWidget(field)
        layout.addWidget(card)

        # About
        layout.addWidget(make_label(ru.SETTINGS_ABOUT, h2=True))
        layout.addWidget(
            make_label(
                ru.ABOUT_TEXT.format(name=ru.APP_TITLE, version=__version__), wrap=True, muted=True
            )
        )
        self.data_btn = make_button(ru.BTN_OPEN_DATA_DIR)
        row2 = QHBoxLayout()
        row2.addWidget(self.data_btn)
        row2.addStretch(1)
        layout.addLayout(row2)
        layout.addStretch(1)

        self.load_from_settings()
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        self.dir_btn.clicked.connect(self._choose_dir)
        self.data_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))
        )

    def load_from_settings(self) -> None:
        s = self._controller.settings
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(s.theme)))
        self.theme_combo.blockSignals(False)
        self.dir_edit.setText(s.export_dir)

    def _theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self._controller.update_settings(replace(self._controller.settings, theme=theme))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)

    def _choose_dir(self) -> None:
        start = self._controller.settings.export_dir
        folder = QFileDialog.getExistingDirectory(self, ru.CHOOSE_FOLDER_TITLE, start)
        if not folder:
            return
        self.dir_edit.setText(folder)
        self._controller.update_settings(replace(self._controller.settings, export_dir=folder))
        self.toast_requested.emit(ru.SETTINGS_SAVED, False)
