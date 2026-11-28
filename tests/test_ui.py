import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from youtube_factory import strings_ru as ru  # noqa: E402
from youtube_factory.app.controller import AppController  # noqa: E402
from youtube_factory.data import db  # noqa: E402
from youtube_factory.data.repositories import AnalysisRepository  # noqa: E402
from youtube_factory.data.settings_store import SettingsStore  # noqa: E402
from youtube_factory.integrations.base import LoadedVideo, VideoSourceError  # noqa: E402
from youtube_factory.models import VideoInfo  # noqa: E402
from youtube_factory.services import demo  # noqa: E402
from youtube_factory.ui import main_window as mw  # noqa: E402
from youtube_factory.ui.views import results_view  # noqa: E402


class FakeSource:
    """Stands in for YouTube so UI tests never touch the network."""

    def __init__(self, error: str = "no_transcript") -> None:
        self.error = error
        self.urls: list[str] = []

    def load(self, url: str):
        self.urls.append(url)
        if self.error:
            raise VideoSourceError(self.error)
        return LoadedVideo(
            VideoInfo("dQw4w9WgXcQ", url, "Видео из сети", "Канал", 600), demo.demo_segments()
        )


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_FACTORY_DATA_DIR", str(tmp_path / "data"))
    repo = AnalysisRepository(db.connect(tmp_path / "h.sqlite3"))
    controller = AppController(repo, SettingsStore(tmp_path / "s.json"), source=FakeSource())
    win = mw.MainWindow(controller)
    qtbot.addWidget(win)
    win.show()
    yield win
    controller.wait()


def run_demo(qtbot, win):
    with qtbot.waitSignal(win.controller.analysis_finished, timeout=15000):
        win.home.example_btn.click()


def test_window_basics(window):
    assert window.windowTitle() == ru.APP_TITLE
    assert window.stack.currentIndex() == mw.PAGE_HOME
    assert window.minimumWidth() >= 900


def test_navigation(qtbot, window):
    window._nav_buttons[mw.PAGE_SETTINGS].click()
    assert window.stack.currentIndex() == mw.PAGE_SETTINGS
    window._nav_buttons[mw.PAGE_HISTORY].click()
    assert window.stack.currentIndex() == mw.PAGE_HISTORY
    window._nav_buttons[mw.PAGE_HOME].click()
    assert window.stack.currentIndex() == mw.PAGE_HOME


def test_empty_url_shows_russian_error(window):
    window.home.url_edit.setText("")
    window.home.create_btn.click()
    assert window.home.error_label.text() == ru.ERR_EMPTY_URL
    window.home.url_edit.setText("https://example.com/x")
    window.home.create_btn.click()
    assert window.home.error_label.text() == ru.ERR_NOT_YOUTUBE


def test_demo_flow_end_to_end(qtbot, window):
    run_demo(qtbot, window)
    assert window.stack.currentIndex() == mw.PAGE_RESULTS
    assert 5 <= len(window.results._cards) <= 10
    assert len(window.controller.history()) == 1


def test_valid_url_without_transcript_explains_how_to_continue(qtbot, window):
    window.home.url_edit.setText("https://youtu.be/dQw4w9WgXcQ")
    with qtbot.waitSignal(window.controller.analysis_failed, timeout=15000):
        window.home.create_btn.click()
    assert window.stack.currentIndex() == mw.PAGE_ANALYSIS
    assert window.analysis.error_label.text() == ru.ERR_NO_TRANSCRIPT
    assert not window.analysis.paste_btn.isHidden()


def test_url_flow_uses_transcript_from_the_source(qtbot, window):
    window.controller.source = FakeSource(error="")
    window.home.url_edit.setText("https://youtu.be/dQw4w9WgXcQ")
    with qtbot.waitSignal(window.controller.analysis_finished, timeout=15000):
        window.home.create_btn.click()
    assert window.stack.currentIndex() == mw.PAGE_RESULTS
    assert window.results.title_label.text() == "Видео из сети"
    assert 5 <= len(window.results._cards) <= 10


@pytest.mark.parametrize(
    ("code", "message", "offers_paste"),
    [
        ("net_offline", ru.ERR_NET_OFFLINE, False),
        ("video_private", ru.ERR_VIDEO_PRIVATE, False),
        ("bot_check", ru.ERR_BOT_CHECK, True),
        ("net_error", ru.ERR_NET_ERROR, True),
    ],
)
def test_source_errors_are_explained_in_russian(qtbot, window, code, message, offers_paste):
    window.controller.source = FakeSource(error=code)
    window.home.url_edit.setText("https://youtu.be/dQw4w9WgXcQ")
    with qtbot.waitSignal(window.controller.analysis_failed, timeout=15000):
        window.home.create_btn.click()
    assert window.analysis.error_label.text() == message
    assert window.analysis.paste_btn.isHidden() is not offers_paste


def test_card_actions(qtbot, window, tmp_path):
    run_demo(qtbot, window)
    view = window.results
    card = view._cards[0]
    short = card.short

    card.copy_btn.click()
    assert short.title in QApplication.clipboard().text()

    card.fav_btn.click()
    assert short.is_favorite
    view.fav_filter.setCurrentIndex(1)
    assert [c for c in view._cards if not c.isHidden()] == [card]
    view.fav_filter.setCurrentIndex(0)

    card.edit_btn.click()
    card.title_edit.setText("Новое название")
    card.save_btn.click()
    assert short.title == "Новое название" and short.is_edited
    stored = window.controller.open_analysis(view._analysis.id).shorts[0]
    assert stored.title == "Новое название" and stored.is_favorite


def test_delete_short_with_confirmation(qtbot, window, monkeypatch):
    run_demo(qtbot, window)
    before = len(window.results._cards)
    monkeypatch.setattr(results_view, "confirm", lambda *a: True)
    window.results._cards[0].delete_btn.click()
    assert len(window.results._cards) == before - 1
    monkeypatch.setattr(results_view, "confirm", lambda *a: False)
    window.results._cards[0].delete_btn.click()
    assert len(window.results._cards) == before - 1


def test_export_selected_and_all(qtbot, window, tmp_path):
    run_demo(qtbot, window)
    view = window.results
    view._cards[1].select_box.setChecked(True)
    out = tmp_path / "выбранные.json"
    assert view.export_to(out, "json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["shorts"]) == 1

    view._cards[1].select_box.setChecked(False)
    csv_path = tmp_path / "все.csv"
    assert view.export_to(csv_path, "csv")
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_export_error_is_reported(qtbot, window, tmp_path):
    run_demo(qtbot, window)
    toasts = []
    window.results.toast_requested.connect(lambda t, e: toasts.append((t, e)))
    assert not window.results.export_to(tmp_path / "нет" / "a.json", "json")
    assert toasts and toasts[-1][1] is True


def test_history_open_and_delete(qtbot, window, monkeypatch):
    run_demo(qtbot, window)
    window.show_page(mw.PAGE_HISTORY)
    item = window.controller.history()[0]
    from youtube_factory.ui.views import history_view

    monkeypatch.setattr(history_view, "confirm", lambda *a: True)
    window.history._delete(item.id)
    assert window.controller.history() == []
    assert window.history.empty_label.isVisible()


def test_theme_change_persists(window, tmp_path):
    combo = window.settings_view.theme_combo
    combo.setCurrentIndex(combo.findData("light"))
    assert window.controller.settings.theme == "light"
    assert SettingsStore(tmp_path / "s.json").load().theme == "light"


def test_cancel_analysis(qtbot, window):
    window.home.example_btn.click()
    with qtbot.waitSignal(window.controller.analysis_cancelled, timeout=15000):
        window.controller.cancel()
    assert not window.analysis.back_btn.isHidden()


def test_cards_are_tall_enough_for_wrapped_text(qtbot, window):
    """Regression: grid rows were shorter than wrapped text needed, so text overlapped."""
    window.resize(1200, 800)
    run_demo(qtbot, window)
    qtbot.wait(150)
    for card in window.results._cards:
        needed = card.layout().heightForWidth(card.width())
        assert card.height() >= needed


def test_results_use_two_columns_on_wide_window(qtbot, window):
    window.resize(1200, 800)
    run_demo(qtbot, window)
    qtbot.wait(150)
    assert window.results._columns == 2
    window.resize(900, 700)
    qtbot.wait(150)
    assert window.results._columns == 1


@pytest.fixture
def motion_restored():
    from youtube_factory.ui.motion import motion

    before = motion.enabled
    yield motion
    motion.enabled = before


def test_animations_switch_persists_and_disables_motion(window, tmp_path, motion_restored):
    assert window.settings_view.anim_switch.isChecked()
    window.settings_view.anim_switch.setChecked(False)
    assert motion_restored.enabled is False
    assert SettingsStore(tmp_path / "s.json").load().animations is False


def test_tween_jumps_when_motion_is_off(window, motion_restored):
    from youtube_factory.ui.motion import Tween

    motion_restored.enabled = False
    tween = Tween(window)
    tween.go(1.0, 500)
    assert tween.value == 1.0 and not tween.running


def test_stepper_spinner_runs_only_while_visible(qtbot, window):
    stepper = window.analysis.stepper
    window.show_page(mw.PAGE_HOME)
    qtbot.wait(50)
    assert not stepper._timer.isActive()
    window.show_page(mw.PAGE_ANALYSIS)
    stepper.set_state(1)
    assert stepper._timer.isActive()
    stepper.set_state(1, failed=True)
    assert not stepper._timer.isActive()


def test_segmented_api_matches_combo_box(qtbot):
    from youtube_factory.ui.widgets.controls import Segmented

    seg = Segmented()
    qtbot.addWidget(seg)
    seg.addItem("A", "a")
    seg.addItem("B", "b")
    changes = []
    seg.currentChanged.connect(changes.append)
    seg.setCurrentIndex(1)
    assert seg.currentData() == "b" and seg.findData("a") == 0 and changes == [1]


def test_pages_are_transparent_so_backdrop_shows(window):
    # Regression: QScrollArea.setWidget re-enabled auto-fill and painted grey pages.
    for scroll in window.findChildren(type(window.results.scroll)):
        assert not scroll.viewport().autoFillBackground()
        assert not scroll.widget().autoFillBackground()


def test_idle_window_has_no_running_animations(qtbot, window):
    qtbot.wait(100)
    assert not window.analysis.stepper._timer.isActive()
    assert not window.stack._fade.running
