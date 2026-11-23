"""Local heuristic engine that proposes Shorts from a timed transcript.

The engine is deterministic and works offline. Generated texts are in Russian
because they are shown directly in the user interface.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from youtube_factory.models import Short, TranscriptSegment

MIN_WINDOW_SEC = 20.0
MAX_WINDOW_SEC = 60.0
IDEAL_MIN_SEC = 30.0
IDEAL_MAX_SEC = 45.0
MIN_WORDS_TOTAL = 30
MIN_SHORTS = 5
MAX_SHORTS = 10

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+(?:-[A-Za-zА-Яа-яЁё0-9]+)*")

HOOK_WORDS = {
    "секрет", "ошибка", "ошибки", "никто", "почему", "представьте", "смотрите",
    "главное", "внимание", "запомните", "никогда", "всегда", "правда", "миф",
    "why", "secret", "mistake", "never", "always", "imagine", "truth", "myth",
}
EMOTION_WORDS = {
    "невероятно", "шок", "ужас", "круто", "потрясающе", "страшно", "лучший",
    "худший", "огромный", "бесплатно", "быстро", "легко", "просто", "опасно",
    "amazing", "incredible", "shocking", "best", "worst", "huge", "free", "easy",
}
CONTRAST_WORDS = {"но", "однако", "зато", "хотя", "while", "but", "however", "although"}

STOPWORDS = {
    "это", "как", "что", "так", "вот", "все", "всё", "его", "она", "они", "мы", "вы",
    "для", "при", "над", "под", "или", "если", "когда", "потому", "очень", "тоже",
    "есть", "быть", "был", "была", "были", "будет", "может", "можно", "нужно",
    "который", "которая", "которые", "только", "уже", "еще", "ещё", "даже", "там",
    "тут", "здесь", "себя", "свой", "наш", "ваш", "этот", "эта", "эти", "того",
    "this", "that", "with", "from", "have", "your", "they", "them", "what", "when",
    "then", "than", "just", "very", "will", "would", "there", "about", "into",
}


class AnalysisError(ValueError):
    """Raised when the transcript is too short or has nothing to analyse."""


class AnalysisCancelled(Exception):
    """Raised when the caller cancels the analysis."""


@dataclass(slots=True)
class _Candidate:
    start_idx: int
    end_idx: int
    start_sec: float
    end_sec: float
    text: str
    score: float
    signals: list[str] = field(default_factory=list)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _keywords(text: str, limit: int) -> list[str]:
    counts = Counter(w for w in _words(text) if len(w) >= 4 and w not in STOPWORDS)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return [w for w, _ in ranked[:limit]]


def _score_window(
    segs: list[TranscriptSegment],
) -> tuple[float, list[str]]:
    text = " ".join(s.text for s in segs)
    words = _words(text)
    first = segs[0].text
    first_words = set(_words(first))
    duration = segs[-1].end_sec - segs[0].start_sec
    score = 30.0
    signals: list[str] = []

    if "?" in first or first_words & HOOK_WORDS:
        score += 18
        signals.append("hook")
    if "?" in text:
        score += 4
    if re.search(r"\d", text):
        score += 8
        signals.append("numbers")
    if set(words) & EMOTION_WORDS:
        score += 10
        signals.append("emotion")
    if set(words) & CONTRAST_WORDS:
        score += 6
        signals.append("contrast")
    if "!" in text:
        score += 3

    if IDEAL_MIN_SEC <= duration <= IDEAL_MAX_SEC:
        score += 14
        signals.append("length")
    elif duration < IDEAL_MIN_SEC:
        score += 14 - (IDEAL_MIN_SEC - duration) * 0.8
    else:
        score += 14 - (duration - IDEAL_MAX_SEC) * 0.8

    density = len(words) / duration if duration > 0 else 0
    if 1.8 <= density <= 3.5:
        score += 6
        signals.append("pace")

    if segs[-1].text.rstrip().endswith((".", "!", "?", "…")):
        score += 4
    return max(0.0, min(100.0, score)), signals


def _build_candidates(segments: list[TranscriptSegment]) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    n = len(segments)
    for i in range(n):
        start = segments[i].start_sec
        for j in range(i, n):
            duration = segments[j].end_sec - start
            if duration > MAX_WINDOW_SEC:
                break
            if duration < MIN_WINDOW_SEC:
                continue
            window = segments[i : j + 1]
            score, signals = _score_window(window)
            text = " ".join(s.text for s in window)
            candidates.append(
                _Candidate(i, j, start, segments[j].end_sec, text, score, signals)
            )
            if duration >= IDEAL_MAX_SEC:
                break
    return candidates


def _target_count(total_sec: float, available: int) -> int:
    wanted = max(MIN_SHORTS, min(MAX_SHORTS, round(total_sec / 90)))
    return min(wanted, available)


def _overlaps(cand: _Candidate, chosen: list[_Candidate]) -> bool:
    return any(cand.start_sec < c.end_sec and c.start_sec < cand.end_sec for c in chosen)


def _select(candidates: list[_Candidate], count: int) -> list[_Candidate]:
    """Pick the best non-overlapping windows; fill with shorter ones if needed."""
    ranked = sorted(candidates, key=lambda c: (-c.score, c.start_sec))
    chosen: list[_Candidate] = []
    for cand in ranked:
        if not _overlaps(cand, chosen):
            chosen.append(cand)
            if len(chosen) >= count:
                break
    if len(chosen) < count:
        # Long windows can crowd out others; retry with the shortest windows first.
        by_length = sorted(
            candidates,
            key=lambda c: (c.end_sec - c.start_sec, -c.score, c.start_sec),
        )
        for cand in by_length:
            if not _overlaps(cand, chosen):
                chosen.append(cand)
                if len(chosen) >= count:
                    break
    return sorted(chosen, key=lambda c: (-c.score, c.start_sec))


def _trim(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-— ")
    return cut + "…"


_TITLE_TEMPLATES = (
    "{a}: главное за {sec} сек",
    "Всё про {a} и {b}",
    "{a} — вот что важно",
    "Как это работает: {a}",
    "{a} и {b}: коротко и по делу",
)

_SIGNAL_TEXT = {
    "hook": "сильное начало, которое цепляет с первой секунды",
    "numbers": "есть конкретные цифры",
    "emotion": "эмоциональная лексика",
    "contrast": "есть противопоставление, которое держит интерес",
    "length": "оптимальная длина для Shorts",
    "pace": "комфортный темп речи",
}


def _make_short(cand: _Candidate, index: int, whole_text: str) -> Short:
    local_kw = _keywords(cand.text, 4) or _keywords(whole_text, 4) or ["видео"]
    a = local_kw[0].capitalize()
    b = local_kw[1] if len(local_kw) > 1 else local_kw[0]
    sec = int(round(cand.end_sec - cand.start_sec))
    title = _TITLE_TEMPLATES[index % len(_TITLE_TEMPLATES)].format(a=a, b=b, sec=sec)

    first_sentence = re.split(r"(?<=[.!?…])\s+", cand.text.strip(), maxsplit=1)[0]
    hook = _trim(first_sentence, 90)
    description = _trim(cand.text, 160) + " Полное видео — на канале."

    tags = ["#shorts"] + [f"#{w}" for w in local_kw[:4]]
    if cand.signals:
        reasons = [_SIGNAL_TEXT[s] for s in cand.signals if s in _SIGNAL_TEXT][:3]
        reason = "Момент может зайти как Short: " + ", ".join(reasons) + "."
    else:
        reason = "Законченная мысль подходящей длины, её удобно смотреть отдельно."
    return Short(
        start_sec=cand.start_sec,
        end_sec=cand.end_sec,
        hook=hook,
        title=_trim(title, 70),
        description=description,
        hashtags=tags,
        score=int(round(cand.score)),
        reason=reason,
    )


def analyze_segments(
    segments: list[TranscriptSegment],
    progress: Callable[[int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[Short]:
    """Return 5-10 Shorts (fewer only if the transcript is too short for that)."""

    def check() -> None:
        if is_cancelled and is_cancelled():
            raise AnalysisCancelled

    def report(step: int) -> None:
        if progress:
            progress(step)

    segments = [s for s in segments if s.text.strip()]
    whole_text = " ".join(s.text for s in segments)
    if len(_words(whole_text)) < MIN_WORDS_TOTAL:
        raise AnalysisError("too_short")
    check()
    report(2)
    candidates = _build_candidates(segments)
    if not candidates:
        raise AnalysisError("no_candidates")
    check()
    report(3)
    total = segments[-1].end_sec - segments[0].start_sec
    chosen = _select(candidates, _target_count(total, len(candidates)))
    check()
    shorts = [_make_short(c, i, whole_text) for i, c in enumerate(chosen)]
    report(4)
    return shorts


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS, or H:MM:SS for long videos."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def format_range(start: float, end: float) -> str:
    return f"{format_time(start)} – {format_time(end)}"
