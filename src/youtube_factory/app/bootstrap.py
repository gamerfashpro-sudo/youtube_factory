"""Qt application start-up and shutdown."""

from __future__ import annotations

import logging
import os
import sys
import tempfile

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from youtube_factory import APP_ID, APP_NAME, __version__
from youtube_factory import strings_ru as ru
from youtube_factory.app.controller import AppController
from youtube_factory.data import db, paths
from youtube_factory.data.logging_setup import setup_logging
from youtube_factory.data.repositories import AnalysisRepository
from youtube_factory.data.settings_store import SettingsStore

log = logging.getLogger(__name__)

SERVER_NAME = f"{APP_NAME}-single-instance"
SMOKE_TIMEOUT_MS = 30_000


def _set_windows_app_id() -> None:
    """Give the process its own taskbar identity on Windows."""
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except (AttributeError, OSError):
            log.warning("Could not set AppUserModelID", exc_info=True)


def _notify_running_instance() -> bool:
    """Ask an already running instance to show itself. True if one answered."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return True
    return False


def _open_repository() -> tuple[AnalysisRepository, bool]:
    try:
        return AnalysisRepository(db.connect(paths.db_path())), True
    except Exception:  # noqa: BLE001 - fall back to an in-memory history
        log.exception("Could not open the history database")
        return AnalysisRepository(db.connect(":memory:")), False


def run(argv: list[str]) -> int:
    smoke = "--smoke-test" in argv
    temp_dir = None
    if smoke:
        # Never touch real user data and leave nothing behind.
        temp_dir = tempfile.TemporaryDirectory(prefix="yf-smoke-")
        os.environ["YOUTUBE_FACTORY_DATA_DIR"] = temp_dir.name
    setup_logging()
    log.info("Starting YouTube Factory %s", __version__)

    _set_windows_app_id()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(ru.APP_TITLE)
    app.setApplicationVersion(__version__)

    if not smoke and _notify_running_instance():
        return 0

    from youtube_factory.ui.fonts import app_font, load_fonts
    from youtube_factory.ui.main_window import MainWindow
    from youtube_factory.ui.theme import theme

    load_fonts()
    app.setFont(app_font())

    repo, db_ok = _open_repository()
    controller = AppController(repo, SettingsStore(paths.settings_path()))
    window = MainWindow(controller)
    theme.watch_system()

    server = None
    if not smoke:
        QLocalServer.removeServer(SERVER_NAME)
        server = QLocalServer()
        server.listen(SERVER_NAME)
        server.newConnection.connect(window.bring_to_front)

    result = {"code": 0}
    if smoke:
        controller.analysis_finished.connect(lambda a: _finish_smoke(app, a, result))
        controller.analysis_failed.connect(lambda *_: _fail_smoke(app, result))
        QTimer.singleShot(SMOKE_TIMEOUT_MS, lambda: _fail_smoke(app, result))
        QTimer.singleShot(0, controller.start_demo)

    window.show()
    if not db_ok:
        window.show_toast(ru.ERR_DB, True)
    code = app.exec()
    controller.wait()
    if server is not None:
        server.close()
    if temp_dir is not None:
        logging.shutdown()
        temp_dir.cleanup()
    return result["code"] or code


def _finish_smoke(app: QApplication, analysis, result: dict) -> None:
    ok = 5 <= len(analysis.shorts) <= 10
    print(f"smoke-test: {len(analysis.shorts)} shorts generated")
    result["code"] = 0 if ok else 1
    app.quit()


def _fail_smoke(app: QApplication, result: dict) -> None:
    print("smoke-test: FAILED")
    result["code"] = 1
    app.quit()
