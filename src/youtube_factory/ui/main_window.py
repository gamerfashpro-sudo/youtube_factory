"""Main window: navigation rail, stacked views and toasts."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.models import Analysis
from youtube_factory.ui import theme
from youtube_factory.ui.views.analysis_view import AnalysisView
from youtube_factory.ui.views.history_view import HistoryView
from youtube_factory.ui.views.home_view import HomeView
from youtube_factory.ui.views.results_view import ResultsView
from youtube_factory.ui.views.settings_view import SettingsView
from youtube_factory.ui.widgets.common import make_button, make_label
from youtube_factory.ui.widgets.toast import Toast
from youtube_factory.ui.widgets.transcript_dialog import TranscriptDialog

PAGE_HOME, PAGE_ANALYSIS, PAGE_RESULTS, PAGE_HISTORY, PAGE_SETTINGS = range(5)


def find_icon() -> QIcon:
    """Locate the app icon in a source checkout or in a PyInstaller bundle."""
    import sys

    candidates = [Path(__file__).resolve().parents[1] / "resources" / "icon.png"]
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        candidates.insert(0, Path(bundle) / "youtube_factory" / "resources" / "icon.png")
    for path in candidates:
        if path.is_file():
            return QIcon(str(path))
    return QIcon()


class MainWindow(QWidget):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle(ru.APP_TITLE)
        self.setWindowIcon(find_icon())
        self.setObjectName("root")
        s = controller.settings
        self.resize(s.window_width, s.window_height)
        self.setMinimumSize(900, 600)
        self._pending_url = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_nav())

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.home = HomeView(controller)
        self.analysis = AnalysisView()
        self.results = ResultsView(controller)
        self.history = HistoryView(controller)
        self.settings_view = SettingsView(controller)
        for view in (self.home, self.analysis, self.results, self.history, self.settings_view):
            self.stack.addWidget(view)

        self.toast = Toast(self)
        self._apply_theme(s.theme)
        self._connect()
        self.show_page(PAGE_HOME)

    # --- construction ---------------------------------------------------------
    def _build_nav(self) -> QFrame:
        nav = QFrame()
        nav.setProperty("nav", True)
        nav.setFixedWidth(200)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(14, 22, 14, 18)
        layout.setSpacing(6)
        layout.addWidget(make_label("YouTube Factory", h2=True))
        layout.addSpacing(14)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons = {}
        for page, title in (
            (PAGE_HOME, ru.NAV_HOME),
            (PAGE_HISTORY, ru.NAV_HISTORY),
            (PAGE_SETTINGS, ru.NAV_SETTINGS),
        ):
            button = make_button(title, nav=True)
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, p=page: self.show_page(p))
            self._nav_group.addButton(button)
            self._nav_buttons[page] = button
            layout.addWidget(button)
        layout.addStretch(1)
        return nav

    def _connect(self) -> None:
        c = self.controller
        c.analysis_started.connect(self._on_started)
        c.analysis_progress.connect(self.analysis.set_step)
        c.analysis_finished.connect(self._on_finished)
        c.analysis_failed.connect(self._on_failed)
        c.analysis_cancelled.connect(self._on_cancelled)
        c.settings_changed.connect(lambda s: self._apply_theme(s.theme))
        self.analysis.cancel_requested.connect(c.cancel)
        self.analysis.back_requested.connect(lambda: self.show_page(PAGE_HOME))
        self.analysis.paste_transcript_requested.connect(lambda: self.ask_transcript(c.last_url))
        self.home.open_analysis.connect(self.open_analysis)
        self.history.open_analysis.connect(self.open_analysis)
        self.home.paste_transcript_requested.connect(self._paste_from_home)
        self.results.new_analysis_requested.connect(lambda: self.show_page(PAGE_HOME))
        for view in (self.results, self.history, self.settings_view):
            view.toast_requested.connect(self.show_toast)

    # --- navigation -----------------------------------------------------------
    def show_page(self, page: int) -> None:
        self.stack.setCurrentIndex(page)
        nav_page = page if page in self._nav_buttons else PAGE_HOME
        self._nav_buttons[nav_page].setChecked(True)

    def open_analysis(self, analysis_id: int) -> None:
        analysis = self.controller.open_analysis(analysis_id)
        if analysis is None:
            return
        self.results.set_analysis(analysis)
        self.show_page(PAGE_RESULTS)

    # --- analysis flow --------------------------------------------------------
    def _paste_from_home(self, url_text: str) -> None:
        if url_text:
            error = self.controller.validate_url(url_text)
            if error:
                self.home.show_error(error)
                return
        self.ask_transcript(url_text)

    def ask_transcript(self, url: str) -> bool:
        dialog = TranscriptDialog(self, self.controller.settings.export_dir)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        self.controller.start_manual(dialog.segments, url=url, title=dialog.video_title)
        if not dialog.timed:
            self.show_toast(ru.UNTIMED_NOTE, False)
        return True

    def _on_started(self) -> None:
        self.analysis.reset()
        self.show_page(PAGE_ANALYSIS)

    def _on_finished(self, analysis: Analysis) -> None:
        self.results.set_analysis(analysis)
        self.show_page(PAGE_RESULTS)

    def _on_failed(self, message: str, offer_paste: bool) -> None:
        self.analysis.show_error(message, offer_paste)

    def _on_cancelled(self) -> None:
        self.analysis.show_cancelled()

    # --- misc -----------------------------------------------------------------
    def show_toast(self, text: str, error: bool = False) -> None:
        self.toast.show_message(text, error)

    def _apply_theme(self, name: str) -> None:
        palette = theme.apply_theme(QApplication.instance(), name)
        self.toast.apply_palette(palette)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if self.toast.isVisible():
            self.toast.reposition()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        self.controller.wait()
        if not (self.isMaximized() or self.isMinimized()):
            from dataclasses import replace

            self.controller.update_settings(
                replace(
                    self.controller.settings,
                    window_width=self.width(),
                    window_height=self.height(),
                )
            )
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange and not self.isMinimized():
            self.toast.reposition()

    def bring_to_front(self) -> None:
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
