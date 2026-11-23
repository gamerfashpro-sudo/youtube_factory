import sqlite3

import pytest

from youtube_factory.data import db, env, paths
from youtube_factory.data.repositories import AnalysisRepository
from youtube_factory.data.settings_store import Settings, SettingsStore
from youtube_factory.integrations.base import IntegrationUnavailableError
from youtube_factory.integrations.stubs import YouTubeApiStub
from youtube_factory.models import Analysis, AnalysisMode, Short, VideoInfo


@pytest.fixture
def repo(tmp_path):
    conn = db.connect(tmp_path / "история.sqlite3")
    yield AnalysisRepository(conn)
    conn.close()


def make_analysis(n=3):
    shorts = [
        Short(i * 40, i * 40 + 35, f"Хук {i}", f"Название {i}", "Описание", ["#shorts"], 50 + i)
        for i in range(n)
    ]
    video = VideoInfo("dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ", "Заголовок", "Канал", 300)
    return Analysis(AnalysisMode.MANUAL, video, shorts)


def test_save_and_get_roundtrip(repo):
    saved = repo.save(make_analysis())
    assert saved.id and all(s.id for s in saved.shorts)
    loaded = repo.get(saved.id)
    assert loaded.video.title == "Заголовок"
    assert loaded.mode == AnalysisMode.MANUAL
    assert [s.title for s in loaded.shorts] == ["Название 0", "Название 1", "Название 2"]
    assert loaded.shorts[1].hashtags == ["#shorts"]


def test_get_missing_returns_none(repo):
    assert repo.get(999) is None


def test_history_order_and_count(repo):
    first = repo.save(make_analysis(2))
    second = repo.save(make_analysis(4))
    items = repo.list_history()
    assert [i.id for i in items] == [second.id, first.id]
    assert [i.shorts_count for i in items] == [4, 2]
    assert len(repo.list_history(limit=1)) == 1


def test_delete_analysis_cascades(repo):
    saved = repo.save(make_analysis())
    repo.delete(saved.id)
    assert repo.get(saved.id) is None
    count = repo._conn.execute("SELECT COUNT(*) FROM shorts").fetchone()[0]
    assert count == 0


def test_edit_favorite_delete_short(repo):
    saved = repo.save(make_analysis())
    sid = saved.shorts[0].id
    repo.update_short_text(sid, "Новый хук", "Новое название", "Новое описание")
    repo.set_favorite(sid, True)
    s = repo.get(saved.id).shorts[0]
    assert (s.hook, s.title, s.description) == ("Новый хук", "Новое название", "Новое описание")
    assert s.is_favorite and s.is_edited
    repo.delete_short(sid)
    assert len(repo.get(saved.id).shorts) == 2


def test_score_constraint(repo):
    saved = repo.save(make_analysis(1))
    with pytest.raises(sqlite3.IntegrityError):
        repo._conn.execute("UPDATE shorts SET score = 101 WHERE id = ?", (saved.shorts[0].id,))


def test_migration_is_idempotent(tmp_path):
    p = tmp_path / "a.sqlite3"
    db.connect(p).close()
    conn = db.connect(p)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    conn.close()


def test_settings_defaults_and_roundtrip(tmp_path):
    store = SettingsStore(tmp_path / "s.json")
    assert store.load() == Settings()
    store.save(Settings(theme="light", export_dir=str(tmp_path / "экспорт")))
    loaded = store.load()
    assert loaded.theme == "light" and loaded.export_dir.endswith("экспорт")
    assert not (tmp_path / "s.json.tmp").exists()


def test_settings_corrupt_file_falls_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json", encoding="utf-8")
    assert SettingsStore(p).load() == Settings()


def test_settings_invalid_values_normalized(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"theme": "neon", "window_width": 5, "unknown": 1}', encoding="utf-8")
    s = SettingsStore(p).load()
    assert s.theme == "dark" and s.window_width == 900


def test_env_file_and_priority(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nLLM_API_KEY="from-file"\nLLM_MODEL=abc\nEMPTY=\n', encoding="utf-8")
    assert env.parse_env_file(f)["LLM_API_KEY"] == "from-file"
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert env.get_secret("LLM_API_KEY", f) == "from-file"
    monkeypatch.setenv("LLM_API_KEY", "from-env")
    assert env.get_secret("LLM_API_KEY", f) == "from-env"
    assert env.get_secret("EMPTY", f) is None
    assert env.get_secret("MISSING", tmp_path / "нет.env") is None


def test_paths_use_override(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_FACTORY_DATA_DIR", str(tmp_path / "данные"))
    assert paths.db_path().parent == tmp_path / "данные"
    assert paths.log_dir().is_dir()


def test_stub_reports_unavailable():
    with pytest.raises(IntegrationUnavailableError):
        YouTubeApiStub().fetch("dQw4w9WgXcQ")
