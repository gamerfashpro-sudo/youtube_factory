from pathlib import Path

from youtube_factory import __version__
from youtube_factory.models import Short


def test_version_is_the_same_everywhere():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in pyproject
    info = (root / "assets" / "version_info.txt").read_text(encoding="utf-8")
    assert f"'ProductVersion', '{__version__}.0'" in info
    assert (root / ".github" / "release-notes" / f"v{__version__}.md").is_file()


def test_score_is_clamped():
    short = Short(0, 10, "h", "t", "d", score=150)
    assert short.score == 100
    assert Short(0, 10, "h", "t", "d", score=-5).score == 0
