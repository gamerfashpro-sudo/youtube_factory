"""Tool installer tests with a fake PyPI. Nothing here touches the network."""

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from youtube_factory.services import tools
from youtube_factory.services.tools import Tool, ToolsCancelled, ToolsError, install_tool

PROGRAM = b"MZ fake program " * 5000


def make_wheel(member: str, payload: bytes = PROGRAM) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(member, payload)
        z.writestr("pkg/__init__.py", "")
    return buf.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def fake_pypi(wheel: bytes, wheel_name: str = "pkg-1.0-py3-none-win_amd64.whl"):
    def open_url(url: str):
        if url.endswith("/json"):
            meta = {"urls": [{"filename": wheel_name, "url": "https://files.example/wheel"}]}
            return FakeResponse(json.dumps(meta).encode())
        assert url == "https://files.example/wheel"
        return FakeResponse(wheel)

    return open_url


def tool_for(wheel: bytes, member: str = "pkg/bin/prog.exe") -> Tool:
    return Tool("prog", "Prog", "pkg", "1.0", hashlib.sha256(wheel).hexdigest(), member, "prog.exe")


def test_pinned_tools_are_complete():
    for tool in tools.TOOLS.values():
        assert len(tool.sha256) == 64 and tool.version and tool.member.endswith(".exe")


def test_install_downloads_verifies_and_unpacks(tmp_path):
    wheel = make_wheel("pkg/bin/prog.exe")
    seen: list[float] = []
    out = install_tool(
        tool_for(wheel), tmp_path, lambda _t, f: seen.append(f), open_url=fake_pypi(wheel)
    )
    assert out == tmp_path / "prog.exe" and out.read_bytes() == PROGRAM
    assert seen[-1] == 1.0 and seen == sorted(seen)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["prog.exe"]  # no leftovers


def test_wrong_hash_is_rejected_and_nothing_is_kept(tmp_path):
    wheel = make_wheel("pkg/bin/prog.exe")
    tool = replace(tool_for(wheel), sha256="0" * 64)
    with pytest.raises(ToolsError) as err:
        install_tool(tool, tmp_path, open_url=fake_pypi(wheel))
    assert err.value.code == "tools_corrupt"
    assert list(tmp_path.iterdir()) == []


def test_missing_member_or_wheel_is_a_download_error(tmp_path):
    wheel = make_wheel("pkg/other.exe")
    with pytest.raises(ToolsError) as err:
        install_tool(tool_for(wheel), tmp_path, open_url=fake_pypi(wheel))
    assert err.value.code == "tools_download_failed"
    with pytest.raises(ToolsError):
        install_tool(tool_for(wheel), tmp_path, open_url=fake_pypi(wheel, "pkg-1.0-linux.whl"))


def test_network_failure_is_a_download_error(tmp_path):
    def offline(_url):
        raise OSError("no network")

    with pytest.raises(ToolsError) as err:
        install_tool(tool_for(b"x"), tmp_path, open_url=offline)
    assert err.value.code == "tools_download_failed"


def test_cancel_stops_the_download(tmp_path):
    wheel = make_wheel("pkg/bin/prog.exe")
    with pytest.raises(ToolsCancelled):
        install_tool(
            tool_for(wheel), tmp_path, is_cancelled=lambda: True, open_url=fake_pypi(wheel)
        )
    assert list(tmp_path.iterdir()) == []


def test_existing_file_is_replaced_atomically(tmp_path):
    (tmp_path / "prog.exe").write_bytes(b"old")
    wheel = make_wheel("pkg/bin/prog.exe")
    install_tool(tool_for(wheel), tmp_path, open_url=fake_pypi(wheel))
    assert (tmp_path / "prog.exe").read_bytes() == PROGRAM


def test_find_tool_prefers_our_copy_and_ensure_skips_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_FACTORY_DATA_DIR", str(tmp_path))
    folder = tools.tools_dir()
    folder.mkdir(parents=True)
    for tool in tools.TOOLS.values():
        (folder / tool.filename).write_bytes(b"x")
    assert tools.find_tool("ffmpeg") == folder / "ffmpeg.exe"
    assert tools.missing_tools() == []

    def forbidden(_url):
        raise AssertionError("must not download when everything is present")

    tools.ensure_tools(open_url=forbidden)


def test_missing_tools_off_windows_is_reported_not_downloaded(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_FACTORY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tools, "find_tool", lambda key: None)
    monkeypatch.setattr(tools, "can_install_here", lambda: False)
    with pytest.raises(ToolsError) as err:
        tools.ensure_tools()
    assert err.value.code == "tools_missing"
    assert isinstance(tools.tools_dir(), Path)
