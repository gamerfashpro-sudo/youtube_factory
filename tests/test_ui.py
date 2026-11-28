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
    assert window.history.empty_state.isVisible()


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


# --- video clips -------------------------------------------------------------------
def open_url_results(qtbot, win):
    win.controller.source = FakeSource(error="")
    win.controller.ensure_tools = lambda progress, cancelled: None
    win.home.url_edit.setText("https://youtu.be/dQw4w9WgXcQ")
    with qtbot.waitSignal(win.controller.analysis_finished, timeout=15000):
        win.home.create_btn.click()


def test_demo_results_cannot_download_clips(qtbot, window):
    run_demo(qtbot, window)
    assert not window.results.clips_btn.isEnabled()
    assert not window.results._cards[0].clip_btn.isEnabled()


def test_download_one_clip_shows_progress_then_done(qtbot, window, tmp_path):
    open_url_results(qtbot, window)
    seen = []

    def fake_maker(req, progress, cancelled):
        progress(0.5)
        seen.append(req)
        return tmp_path / f"clip{req.index}.mp4"

    window.controller.clip_maker = fake_maker
    card = window.results._cards[1]
    assert card.clip_btn.isEnabled() and card.clip_state == "idle"
    with qtbot.waitSignal(window.controller.clips_finished, timeout=5000):
        card.clip_btn.click()
    assert len(seen) == 1 and seen[0].start_sec == card.short.start_sec
    assert card.clip_state == "done" and "clip1.mp4" in card.clip_label.text()
    assert not card.open_btn.isHidden()
    others = [c for c in window.results._cards if c is not card]
    assert all(c.clip_state == "idle" for c in others)
    assert window.results.clips_btn.text() == ru.BTN_MAKE_ALL
    assert window.toast.text().startswith("Готово")


def test_selected_cards_are_downloaded_and_failures_are_explained(qtbot, window, tmp_path):
    open_url_results(qtbot, window)
    from youtube_factory.services.clipper import ClipError

    def fake_maker(req, progress, cancelled):
        if req.index == 2:  # second request of the batch = third card
            raise ClipError("clip_download_failed")
        return tmp_path / "ok.mp4"

    window.controller.clip_maker = fake_maker
    cards = window.results._cards
    cards[0].select_box.setChecked(True)
    cards[2].select_box.setChecked(True)
    assert window.results.clips_btn.text() == ru.BTN_MAKE_SELECTED
    with qtbot.waitSignal(window.controller.clips_finished, timeout=5000):
        window.results.clips_btn.click()
    assert cards[0].clip_state == "done"
    assert cards[2].clip_state == "failed"
    assert cards[2].clip_label.text() == ru.CLIP_FAILED.format(reason=ru.ERR_CLIP_DOWNLOAD)
    assert cards[1].clip_state == "idle"
    assert window.results.status_label.text().startswith("Готово 1 из 2")


def test_stop_button_cancels_the_batch(qtbot, window):
    import threading

    open_url_results(qtbot, window)
    gate = threading.Event()

    def slow_maker(req, progress, cancelled):
        gate.wait(5)
        from youtube_factory.services.clipper import ClipCancelled

        if cancelled():
            raise ClipCancelled
        return None

    window.controller.clip_maker = slow_maker
    window.results.clips_btn.click()
    qtbot.waitUntil(lambda: window.controller.clips_running, timeout=2000)
    assert window.results.clips_btn.text() == ru.BTN_CANCEL_CLIPS
    with qtbot.waitSignal(window.controller.clips_finished, timeout=5000):
        window.results.clips_btn.click()  # now acts as "stop"
        gate.set()
    assert all(c.clip_state == "idle" for c in window.results._cards)
    assert "Остановлено" in window.results.status_label.text()


def test_clip_settings_persist(window, tmp_path):
    view = window.settings_view
    view.style_combo.setCurrentIndex(view.style_combo.findData("crop"))
    assert window.controller.settings.clip_style == "crop"
    assert SettingsStore(tmp_path / "s.json").load().clip_style == "crop"
    assert view.clips_dir_edit.text().endswith("YouTube Factory")


# --- glow ---------------------------------------------------------------------------
def test_primary_button_glows_and_follows_its_state(qtbot):
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    from youtube_factory.ui.widgets.controls import GlassButton
    from youtube_factory.ui.widgets.glow import GlowHalo

    host = QWidget()
    lay = QVBoxLayout(host)
    btn = GlassButton("Ок", "primary")
    other = GlassButton("Нет", "secondary")
    lay.addWidget(btn)
    lay.addWidget(other)
    qtbot.addWidget(host)
    host.show()

    halo = btn._halo
    assert isinstance(halo, GlowHalo) and halo.isVisible()
    assert other._halo is None  # only primary buttons glow
    assert halo.geometry().contains(btn.geometry())

    btn.setEnabled(False)
    assert not halo.isVisible()
    btn.setEnabled(True)
    assert halo.isVisible()
    btn.variant = "secondary"
    assert not halo.isVisible()
    btn.variant = "primary"
    assert halo.isVisible()

    btn.deleteLater()
    qtbot.waitUntil(lambda: not host.findChildren(GlowHalo), timeout=2000)


# --- empty screens and backdrop ----------------------------------------------------------
def test_empty_history_offers_a_first_analysis(qtbot, window):
    window.show_page(mw.PAGE_HISTORY)
    state = window.history.empty_state
    assert state.isVisibleTo(window.history)
    assert state.action_btn is not None
    state.action_btn.click()
    assert window.stack.currentIndex() == mw.PAGE_HOME


def test_empty_favorites_explains_and_returns_to_all(qtbot, window):
    run_demo(qtbot, window)
    results = window.results
    results.fav_filter.setCurrentIndex(1)
    state = results.empty_state
    assert state.isVisibleTo(results)
    assert state.title_label.text() == ru.EMPTY_FAVORITES_TITLE
    assert state.action_btn.isVisibleTo(state)
    state.action_btn.click()
    assert results.fav_filter.currentData() == "all"
    assert not state.isVisibleTo(results)


def test_home_shows_a_compact_empty_state_without_history(window):
    from youtube_factory.ui.widgets.empty_state import EmptyState

    window.show_page(mw.PAGE_HOME)
    window.home.refresh_recent()
    states = window.home.findChildren(EmptyState)
    assert states and states[0].title_label.text() == ru.EMPTY_RECENT_TITLE


def test_empty_art_pops_in_once_and_ends_fully_visible(qtbot):
    from youtube_factory.ui.widgets.empty_state import EmptyArt

    art = EmptyArt("clock")
    qtbot.addWidget(art)
    art.show()
    qtbot.waitUntil(lambda: art._appear.value == 1.0, timeout=2000)
    assert not art._appear.running


def test_backdrop_grain_is_tiny_and_balanced():
    from youtube_factory.ui import backdrop

    brush = backdrop.grain_brush()
    assert backdrop.grain_brush() is brush  # made once
    img = brush.texture().toImage()
    alphas = [img.pixelColor(x, y).alpha() for x in range(0, 128, 7) for y in range(0, 128, 7)]
    assert max(alphas) <= backdrop.GRAIN_MAX_ALPHA


# --- micro animations ---------------------------------------------------------------------
def test_cards_fade_in_once_and_leave_no_effect_behind(qtbot, window, motion_restored):
    motion_restored.enabled = True
    run_demo(qtbot, window)
    cards = window.results._cards
    assert any(c.graphicsEffect() is not None for c in cards)  # the animation is running
    qtbot.waitUntil(lambda: all(c.graphicsEffect() is None for c in cards), timeout=5000)


def test_cards_appear_at_once_when_animations_are_off(qtbot, window, motion_restored):
    motion_restored.enabled = False
    run_demo(qtbot, window)
    assert all(c.graphicsEffect() is None for c in window.results._cards)


def test_copy_flashes_a_check_mark_then_restores_the_icon(qtbot, window):
    run_demo(qtbot, window)
    btn = window.results._cards[0].copy_btn
    assert btn._icon == "copy"
    btn.flash_done(ms=150)
    assert btn._icon == "check"
    btn.flash_done(ms=150)  # a second click while flashing must not forget the real icon
    qtbot.waitUntil(lambda: btn._icon == "copy", timeout=2000)
    assert btn._flash_icon is None
