from youtube_factory import __version__
from youtube_factory.models import Short


def test_version():
    assert __version__ == "0.1.0"


def test_score_is_clamped():
    short = Short(0, 10, "h", "t", "d", score=150)
    assert short.score == 100
    assert Short(0, 10, "h", "t", "d", score=-5).score == 0
