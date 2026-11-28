"""Main window: navigation rail, stacked views and toasts."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon, QPainter
from PySide6.QtWidgets import QDialog, QHBoxLayout, QWidget

from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.data.paths import resource_dir
from youtube_factory.data.settings_store import Settings
from youtube_factory.models import Analysis
from youtube_factory.ui import winfx
from youtube_factory.ui.backdrop import paint_backdrop
from youtube_factory.ui.motion import motion
from youtube_factory.ui.theme import theme
from youtube_factory.ui.views.analysis_view import AnalysisView
from youtube_factory.ui.views.history_view import HistoryView
from youtube_factory.ui.views.home_view import HomeView
from youtube_factory.ui.views.results_view import ResultsView
from youtube_factory.ui.views.settings_view import SettingsView
from youtube_factory.ui.widgets.dialogs import TranscriptDialog
from youtube_factory.ui.widgets.fade_stack import FadeStack
from youtube_factory.ui.widgets.nav_dock import NavDock
from youtube_factory.ui.widgets.toast import Toast

PAGE_HOME, PAGE_ANALYSIS, PAGE_RESULTS, PAGE_HISTORY, PAGE_SETTINGS = range(5)


def find_icon() -> QIcon:
    """Locate the app icon in a source checkout or in a PyInstaller bundle."""
    path = resource_dir() / "icon.png"
    return QIcon(str(path)) if path.is_file() else QIcon()


class MainWindow(QWidget):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle(ru.APP_TITLE)
        self.setWindowIcon(find_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        st = controller.settings
        self.resize(st.window_width, st.window_height)
        self.setMinimumSize(900, 600)
        self._pending_url = ""
        motion.enabled = st.animations
        theme.set_choice(st.theme)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 0, 16)
        root.setSpacing(0)
        self.dock = NavDock()
        for page, title, icon in (
            (PAGE_HOME, ru.NAV_HOME, "home"),
            (PAGE_HISTORY, ru.NAV_HISTORY, "clock"),
            (PAGE_SETTINGS, ru.NAV_SETTINGS, "sliders"),
        ):
            item = self.dock.add_item(page, title, icon)
            item.clicked.connect(lambda _=False, p=page: self.show_page(p))
        self._nav_buttons = self.dock.items
        root.addWidget(self.dock)

        self.stack = FadeStack()
        root.addWidget(self.stack, 1)
        self.home = HomeView(controller)
        self.analysis = AnalysisView()
        self.results = ResultsView(controller)
        self.history = HistoryView(controller)
        self.settings_view = SettingsView(controller)
        for view in (self.home, self.analysis, self.results, self.history, self.settings_view):
            self.stack.addWidget(view)

        self.toast = Toast(self)
        theme.changed.connect(self._on_theme_changed)
        self._connect()
        self.show_page(PAGE_HOME)

    # --- construction ---------------------------------------------------------
    def _connect(self) -> None:
        c = self.controller
        c.analysis_started.connect(self._on_started)
        c.analysis_progress.connect(self.analysis.set_step)
        c.analysis_finished.connect(self._on_finished)
        c.analysis_failed.connect(self._on_failed)
        c.analysis_cancelled.connect(self._on_cancelled)
        c.settings_changed.connect(self._apply_settings)
        self.analysis.cancel_requested.connect(c.cancel)
        self.analysis.back_requested.connect(lambda: self.show_page(PAGE_HOME))
        self.analysis.paste_transcript_requested.connect(lambda: self.ask_transcript(c.last_url))
        self.home.open_analysis.connect(self.open_analysis)
        self.home.history_requested.connect(lambda: self.show_page(PAGE_HISTORY))
        self.history.open_analysis.connect(self.open_analysis)
        self.history.new_analysis_requested.connect(lambda: self.show_page(PAGE_HOME))
        self.home.paste_transcript_requested.connect(self._paste_from_home)
        self.results.new_analysis_requested.connect(lambda: self.show_page(PAGE_HOME))
        for view in (self.results, self.history, self.settings_view):
            view.toast_requested.connect(self.show_toast)

    # --- navigation -----------------------------------------------------------
    def show_page(self, page: int) -> None:
        self.stack.setCurrentIndex(page)
        self.dock.set_current(page if page in self._nav_buttons else PAGE_HOME)

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

    def _apply_settings(self, st: Settings) -> None:
        motion.enabled = st.animations
        theme.set_choice(st.theme)

    def _on_theme_changed(self) -> None:
        winfx.style_title_bar(self, theme.p.dark, theme.p.base, theme.p.text)
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        winfx.style_title_bar(self, theme.p.dark, theme.p.base, theme.p.text)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        paint_backdrop(p, event.rect(), self.size(), theme.p)

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
