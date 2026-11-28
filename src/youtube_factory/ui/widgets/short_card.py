"""Card showing one generated Short with inline editing."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QTimer, Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QVBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.models import Short
from youtube_factory.services.analyzer import format_range
from youtube_factory.ui.motion import motion
from youtube_factory.ui.widgets.common import make_label, set_paragraph
from youtube_factory.ui.widgets.controls import CheckPill, Chip, GlassButton, icon_button
from youtube_factory.ui.widgets.fields import GlassLineEdit, GlassTextEdit
from youtube_factory.ui.widgets.glass import GlassPanel
from youtube_factory.ui.widgets.viz import ProgressLine, ScoreRing, TimelineBar


class ShortCard(GlassPanel):
    copy_requested = Signal(object)
    save_requested = Signal(object, str, str, str)
    favorite_toggled = Signal(object)
    delete_requested = Signal(object)
    selection_changed = Signal()
    make_clip_requested = Signal(object)
    open_folder_requested = Signal()

    def __init__(self, short: Short, total_sec: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent, hoverable=True)
        self.short = short
        self.clip_state = "idle"
        self._total = total_sec
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.select_box = CheckPill(ru.SELECT_FOR_EXPORT)
        self.select_box.toggled.connect(lambda _=False: self.selection_changed.emit())
        self.time_chip = Chip("", "time", "clock")
        self.score_ring = ScoreRing(46)
        self.score_ring.setToolTip(ru.SCORE_LABEL)
        top.addWidget(self.select_box)
        top.addWidget(self.time_chip)
        top.addStretch(1)
        top.addWidget(make_label(ru.SCORE_LABEL, role="small"))
        top.addWidget(self.score_ring)
        root.addLayout(top)

        self.timeline = TimelineBar()
        root.addWidget(self.timeline)
        root.addSpacing(2)

        self.hook_label = make_label(wrap=True, role="h3")
        self.title_label = make_label(wrap=True, role="body")
        self.desc_label = make_label(wrap=True, role="muted")
        self.tags_label = make_label(wrap=True, role="accent")
        self.reason_label = make_label(wrap=True, role="small")
        for w in (self.hook_label, self.title_label, self.desc_label, self.tags_label):
            root.addWidget(w)
        root.addWidget(self.reason_label)

        self.edit_panel = QWidget()
        edit = QVBoxLayout(self.edit_panel)
        edit.setContentsMargins(0, 0, 0, 0)
        edit.setSpacing(6)
        self.hook_edit = GlassLineEdit(height=40)
        self.title_edit = GlassLineEdit(height=40)
        self.desc_edit = GlassTextEdit()
        self.desc_edit.setFixedHeight(96)
        for caption, widget in (
            (ru.LABEL_HOOK, self.hook_edit),
            (ru.LABEL_TITLE, self.title_edit),
            (ru.LABEL_DESCRIPTION, self.desc_edit),
        ):
            edit.addWidget(make_label(caption, role="small"))
            edit.addWidget(widget)
        edit_buttons = QHBoxLayout()
        self.save_btn = GlassButton(ru.BTN_SAVE, "primary", "check", height=38)
        self.cancel_btn = GlassButton(ru.BTN_CANCEL, "ghost", height=38)
        edit_buttons.addWidget(self.save_btn)
        edit_buttons.addWidget(self.cancel_btn)
        edit_buttons.addStretch(1)
        edit.addSpacing(4)
        edit.addLayout(edit_buttons)
        self.edit_panel.hide()
        root.addWidget(self.edit_panel)
        # Extra height (from a taller neighbour in the grid row) goes here, not between labels.
        root.addStretch(1)

        self.actions = QWidget()
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(0, 6, 0, 0)
        actions.setSpacing(6)
        self.clip_btn = GlassButton(
            ru.BTN_MAKE_CLIP, "primary", "film", ru.TIP_MAKE_CLIP, height=36
        )
        # Icon-only so the whole row fits a two-column card at the minimum window width.
        self.copy_btn = icon_button("copy", ru.TIP_COPY)
        self.edit_btn = icon_button("edit", ru.TIP_EDIT)
        self.fav_btn = icon_button("star", ru.TIP_FAVORITE)
        self.delete_btn = icon_button("trash", ru.TIP_DELETE, "danger")
        for b in (self.clip_btn, self.copy_btn, self.edit_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.fav_btn)
        actions.addWidget(self.delete_btn)
        root.addWidget(self.actions)

        # Status of the video clip for this Short (hidden until a download starts).
        self.clip_box = QWidget()
        clip = QVBoxLayout(self.clip_box)
        clip.setContentsMargins(0, 2, 0, 0)
        clip.setSpacing(6)
        clip_row = QHBoxLayout()
        clip_row.setSpacing(8)
        self.clip_label = make_label(role="small")
        self.clip_label.setMinimumHeight(30)  # same row height with or without the folder button
        self.open_btn = GlassButton(ru.BTN_OPEN_CLIPS, "ghost", "folder", height=30)
        clip_row.addWidget(self.clip_label, 1)
        clip_row.addWidget(self.open_btn)
        clip.addLayout(clip_row)
        self.clip_bar = ProgressLine()
        clip.addWidget(self.clip_bar)
        self.clip_box.hide()
        root.addWidget(self.clip_box)

        self.clip_btn.clicked.connect(lambda: self.make_clip_requested.emit(self.short))
        self.open_btn.clicked.connect(self.open_folder_requested)
        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.short))
        self.edit_btn.clicked.connect(self._start_edit)
        self.cancel_btn.clicked.connect(self._stop_edit)
        self.save_btn.clicked.connect(self._save)
        self.fav_btn.clicked.connect(lambda: self.favorite_toggled.emit(self.short))
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.short))
        self.refresh()

    def is_selected(self) -> bool:
        return self.select_box.isChecked()

    def refresh(self, animate_fav: bool = False) -> None:
        s = self.short
        self.time_chip.setText(format_range(s.start_sec, s.end_sec))
        self.score_ring.set_score(s.score)
        self.timeline.set_range(s.start_sec, s.end_sec, self._total)
        set_paragraph(self.hook_label, f"«{s.hook}»", 130)
        set_paragraph(self.title_label, f"{ru.LABEL_TITLE}: {s.title}", 135)
        set_paragraph(self.desc_label, s.description, 140)
        self.tags_label.setText(" ".join(s.hashtags))
        set_paragraph(self.reason_label, f"{ru.LABEL_REASON}: {s.reason}", 135)
        self.fav_btn.set_active(s.is_favorite, animate=animate_fav)
        self.fav_btn.setToolTip(ru.TIP_UNFAVORITE if s.is_favorite else ru.TIP_FAVORITE)

    def set_clip_state(self, state: str, text: str = "", fraction: float = 0.0) -> None:
        """state: idle, queued, working, done or failed."""
        self.clip_box.setVisible(state != "idle")
        self.clip_label.setText(text)
        self.clip_label.setProperty("role", "error" if state == "failed" else "small")
        self.clip_label.style().unpolish(self.clip_label)
        self.clip_label.style().polish(self.clip_label)
        self.clip_bar.kind = {"done": "done", "failed": "failed"}.get(state, "work")
        self.clip_bar.set_value(1.0 if state == "done" else fraction, animate=state == "working")
        self.open_btn.setVisible(state == "done")
        self.clip_btn.setEnabled(state not in ("queued", "working"))
        self.clip_state = state

    def reveal(self, delay_ms: int) -> None:
        """Fade the card in after a short delay. The effect is removed when done."""
        if not motion.enabled:
            return
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(360)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(anim.start)
        timer.start(delay_ms)

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
