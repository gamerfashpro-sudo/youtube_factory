"""Card showing one generated Short with inline editing."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from youtube_factory import strings_ru as ru
from youtube_factory.models import Short
from youtube_factory.services.analyzer import format_range
from youtube_factory.ui.widgets.common import make_button, make_label, set_prop


class ShortCard(QFrame):
    copy_requested = Signal(object)
    save_requested = Signal(object, str, str, str)
    favorite_toggled = Signal(object)
    delete_requested = Signal(object)
    selection_changed = Signal()

    def __init__(self, short: Short, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.short = short
        self.setProperty("card", True)
        self.setMinimumWidth(340)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.select_box = QCheckBox()
        self.select_box.setToolTip(ru.SELECT_FOR_EXPORT)
        self.select_box.toggled.connect(lambda _=False: self.selection_changed.emit())
        self.time_label = make_label(time=True)
        self.score_label = make_label(score=True)
        top.addWidget(self.select_box)
        top.addWidget(self.time_label)
        top.addStretch(1)
        top.addWidget(make_label(ru.SCORE_LABEL, muted=True))
        top.addWidget(self.score_label)
        root.addLayout(top)

        self.hook_label = make_label(wrap=True)
        self.hook_label.setStyleSheet("font-weight: 600; font-size: 12pt;")
        self.title_label = make_label(wrap=True)
        self.desc_label = make_label(wrap=True, muted=True)
        self.tags_label = make_label(wrap=True, time=True)
        self.reason_label = make_label(wrap=True, muted=True)
        for w in (self.hook_label, self.title_label, self.desc_label, self.tags_label):
            root.addWidget(w)
        root.addWidget(self.reason_label)

        self.edit_panel = QWidget()
        edit = QVBoxLayout(self.edit_panel)
        edit.setContentsMargins(0, 0, 0, 0)
        self.hook_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setFixedHeight(90)
        for caption, widget in (
            (ru.LABEL_HOOK, self.hook_edit),
            (ru.LABEL_TITLE, self.title_edit),
            (ru.LABEL_DESCRIPTION, self.desc_edit),
        ):
            edit.addWidget(make_label(caption, muted=True))
            edit.addWidget(widget)
        edit_buttons = QHBoxLayout()
        self.save_btn = make_button(ru.BTN_SAVE, primary=True)
        self.cancel_btn = make_button(ru.BTN_CANCEL)
        edit_buttons.addWidget(self.save_btn)
        edit_buttons.addWidget(self.cancel_btn)
        edit_buttons.addStretch(1)
        edit.addLayout(edit_buttons)
        self.edit_panel.hide()
        root.addWidget(self.edit_panel)

        self.actions = QWidget()
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(0, 4, 0, 0)
        self.copy_btn = make_button(ru.BTN_COPY, ru.TIP_COPY)
        self.edit_btn = make_button(ru.BTN_EDIT, ru.TIP_EDIT)
        self.fav_btn = make_button("")
        self.delete_btn = make_button(ru.BTN_DELETE, ru.TIP_DELETE, danger=True)
        for b in (self.copy_btn, self.edit_btn, self.fav_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.delete_btn)
        root.addWidget(self.actions)

        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.short))
        self.edit_btn.clicked.connect(self._start_edit)
        self.cancel_btn.clicked.connect(self._stop_edit)
        self.save_btn.clicked.connect(self._save)
        self.fav_btn.clicked.connect(lambda: self.favorite_toggled.emit(self.short))
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.short))
        self.refresh()

    def is_selected(self) -> bool:
        return self.select_box.isChecked()

    def refresh(self) -> None:
        s = self.short
        self.time_label.setText(format_range(s.start_sec, s.end_sec))
        self.score_label.setText(str(s.score))
        self.hook_label.setText(f"«{s.hook}»")
        self.title_label.setText(f"{ru.LABEL_TITLE}: {s.title}")
        self.desc_label.setText(s.description)
        self.tags_label.setText(" ".join(s.hashtags))
        self.reason_label.setText(f"{ru.LABEL_REASON}: {s.reason}")
        self.fav_btn.setText(ru.FAV_ON if s.is_favorite else ru.FAV_OFF)
        self.fav_btn.setToolTip(ru.TIP_UNFAVORITE if s.is_favorite else ru.TIP_FAVORITE)
        set_prop(self.fav_btn, "fav", s.is_favorite)

    def _start_edit(self) -> None:
        self.hook_edit.setText(self.short.hook)
        self.title_edit.setText(self.short.title)
        self.desc_edit.setPlainText(self.short.description)
        self.edit_panel.show()
        self.actions.hide()
        self.hook_edit.setFocus()

    def _stop_edit(self) -> None:
        self.edit_panel.hide()
        self.actions.show()

    def _save(self) -> None:
        hook = self.hook_edit.text().strip() or self.short.hook
        title = self.title_edit.text().strip() or self.short.title
        description = self.desc_edit.toPlainText().strip() or self.short.description
        self.save_requested.emit(self.short, hook, title, description)
        self._stop_edit()
        self.refresh()
