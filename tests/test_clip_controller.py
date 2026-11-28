"""Batch clip making through the controller, with a fake clip maker (no ffmpeg, no network)."""

import threading

import pytest

pytest.importorskip("PySide6")

from youtube_factory import strings_ru as ru  # noqa: E402
from youtube_factory.app.controller import AppController  # noqa: E402
from youtube_factory.data import db  # noqa: E402
from youtube_factory.data.repositories import AnalysisRepository  # noqa: E402
from youtube_factory.data.settings_store import Settings, SettingsStore  # noqa: E402
from youtube_factory.models import Short, VideoInfo  # noqa: E402
from youtube_factory.services.clipper import ClipCancelled, ClipError  # noqa: E402

VIDEO = VideoInfo("dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Тест", "К", 600)


def make_shorts(n: int = 3) -> list[Short]:
    return [Short(10.0 * i, 10.0 * i + 8, f"h{i}", f"t{i}", "d") for i in range(n)]


@pytest.fixture
def controller(tmp_path):
    repo = AnalysisRepository(db.connect(tmp_path / "h.sqlite3"))
    ctrl = AppController(repo, SettingsStore(tmp_path / "s.json"))
    ctrl.update_settings(Settings(clips_dir=str(tmp_path / "clips"), clip_style="crop"))
    ctrl.ensure_tools = lambda progress, cancelled: None  # tools are tested separately
    yield ctrl
    ctrl.wait()


def test_demo_video_cannot_be_clipped(controller):
    assert not controller.can_make_clips(VideoInfo("", "", "Демо"))
    assert controller.start_clips(VideoInfo("", "", "Демо"), make_shorts()) is False
    assert controller.can_make_clips(VIDEO)


def test_batch_reports_each_clip_and_a_summary(qtbot, controller, tmp_path):
    requests = []

    def fake(req, progress, cancelled):
        requests.append(req)
        progress(0.5)
        if req.index == 2:
            raise ClipError("clip_download_failed")
        return req.out_dir / f"clip{req.index}.mp4"

    controller.clip_maker = fake
    done, failed, started = [], [], []
    controller.clip_done.connect(lambda s, p: done.append((s.hook, p)))
    controller.clip_failed.connect(lambda s, r: failed.append((s.hook, r)))
    controller.clip_started.connect(lambda s: started.append(s.hook))
    shorts = make_shorts()
    with qtbot.waitSignal(controller.clips_finished, timeout=5000) as blocker:
        assert controller.start_clips(VIDEO, shorts)
    assert blocker.args == [2, 1, False, str(tmp_path / "clips")]
    assert started == ["h0", "h1", "h2"]
    assert [d[0] for d in done] == ["h0", "h2"]
    assert failed == [("h1", ru.ERR_CLIP_DOWNLOAD)]
    # Settings reach the request.
    assert {r.style for r in requests} == {"crop"}
    assert [r.index for r in requests] == [1, 2, 3]
    assert requests[0].url == VIDEO.url and requests[0].video_duration == 600


def test_unexpected_error_in_one_clip_does_not_stop_the_batch(qtbot, controller):
    def fake(req, progress, cancelled):
        if req.index == 1:
            raise RuntimeError("boom")
        return req.out_dir / "x.mp4"

    controller.clip_maker = fake
    failed = []
    controller.clip_failed.connect(lambda s, r: failed.append(r))
    with qtbot.waitSignal(controller.clips_finished, timeout=5000) as blocker:
        controller.start_clips(VIDEO, make_shorts(2))
    assert blocker.args[:3] == [1, 1, False]
    assert failed == [ru.ERR_UNKNOWN.rstrip(".").lower()]


def test_cancel_stops_the_queue(qtbot, controller):
    gate = threading.Event()

    def fake(req, progress, cancelled):
        gate.wait(5)
        if cancelled():
            raise ClipCancelled
        return req.out_dir / "x.mp4"

    controller.clip_maker = fake
    with qtbot.waitSignal(controller.clips_finished, timeout=5000) as blocker:
        controller.start_clips(VIDEO, make_shorts(3))
        controller.cancel_clips()
        gate.set()
    assert blocker.args[:3] == [0, 0, True]
    assert not controller.clips_running


def test_second_batch_is_ignored_while_one_runs(qtbot, controller):
    gate = threading.Event()
    controller.clip_maker = lambda req, progress, cancelled: (gate.wait(5), req.out_dir / "x.mp4")[
        1
    ]
    assert controller.start_clips(VIDEO, make_shorts(1))
    assert controller.start_clips(VIDEO, make_shorts(1)) is False
    with qtbot.waitSignal(controller.clips_finished, timeout=5000):
        gate.set()


def test_default_folder_and_style_are_used_when_unset(tmp_path):
    repo = AnalysisRepository(db.connect(tmp_path / "h.sqlite3"))
    ctrl = AppController(repo, SettingsStore(tmp_path / "s2.json"))
    assert ctrl.settings.clip_style == "blur"
    assert ctrl.clips_folder().endswith("YouTube Factory")
    bad = Settings(clip_style="nonsense").normalized()
    assert bad.clip_style == "blur"


def test_failed_tool_download_fails_every_clip_with_a_clear_reason(qtbot, controller):
    from youtube_factory.services.tools import ToolsError

    def no_internet(progress, cancelled):
        progress("ffmpeg", 0.3)
        raise ToolsError("tools_download_failed")

    controller.ensure_tools = no_internet
    controller.clip_maker = lambda *a: pytest.fail("no clip may start without tools")
    preparing, failed = [], []
    controller.clips_preparing.connect(lambda t, f: preparing.append((t, f)))
    controller.clip_failed.connect(lambda s, r: failed.append(r))
    with qtbot.waitSignal(controller.clips_finished, timeout=5000) as blocker:
        controller.start_clips(VIDEO, make_shorts(2))
    assert preparing == [("ffmpeg", 0.3)]
    assert failed == [ru.ERR_TOOLS_DOWNLOAD] * 2
    assert blocker.args[:3] == [0, 2, False]


def test_demo_mode_never_makes_clips_even_with_a_real_video_id(controller):
    from youtube_factory.models import AnalysisMode

    assert not controller.can_make_clips(VIDEO, AnalysisMode.DEMO)
    assert controller.start_clips(VIDEO, make_shorts(1), AnalysisMode.DEMO) is False
    assert not controller.clips_running
