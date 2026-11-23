# YouTube Factory — Implementation Plan (v0.1.0)

Status: **DRAFT, awaiting approval.** No application code has been written yet.

## 0. Repository audit

- Repo: `gamerfashpro-sudo/youtube_factory`, branch `main`, 1 commit (`49dbc60 Add files via upload`).
- Existing content: `README.md` (9 bytes, placeholder `# pogoda-`) and `pogoda-widget@example.com.zip`.
- Protected file fingerprint (taken before any change):
  - SHA-256: `a2c8260fceb7ca8aa5b4dfe6e3880461d493e833ecfc29114b6a2d453cebc607`
  - Size: 118148 bytes
  - Git blob: `318eee31d59188bf059595ddeeb75d38dd7bf9be`
- Protection rules for this project:
  - Never `git rm`, `git mv`, `git add` over, or rewrite the zip. No force-push, no history rewrite.
  - `.gitignore` must not match it. PyInstaller `--add-data` and `.spec` never reference it.
  - A CI step and a local script (`scripts/verify_protected_file.py`) compare the blob hash above and fail the build if it changed.
- `README.md` is a 9-byte placeholder. Plan: replace it with the real README (it is not the protected file). **Needs your OK**, see "Open questions".

## 1. Architecture

Stack: Python 3.11+, PySide6, SQLite (stdlib `sqlite3`), PyInstaller (onefile, windowed), pytest, ruff.

Layers (dependencies point downward only):

```
ui/            Qt widgets, views, theme, toasts. No business logic.
  |
app/           Controllers/presenters, Qt workers (QThread/QRunnable), signals.
  |
services/      Pure logic: URL parsing, transcript parsing, analysis, export.
  |
data/          SQLite repositories, settings store, paths, logging setup.
  |
integrations/  Adapter interfaces (stubs in v0.1.0): YouTube Data API,
               transcript providers, LLM providers.
```

Key decisions:
- **Analysis engine (local, no AI):** parse transcript into timed segments, split into candidate windows (20–60 s), score each by heuristics (question/hook phrases, numbers, emotional/contrast words, density, sentence completeness, length fit), pick top 5–10 non-overlapping windows, then build hook/title/description/hashtags from templates plus extracted keywords. Russian and English stopword lists. Deterministic, fully testable.
- **Demo mode:** bundled Russian demo transcript and precomputed Shorts in a JSON resource; works offline.
- **Manual transcript mode:** paste text or open `.txt` / `.srt` / `.vtt`. Plain text without timestamps gets synthetic timing (estimated from word count at ~150 wpm), clearly labeled in the UI.
- **No network in v0.1.0.** Video metadata (title, channel, thumbnail) comes from demo data or user-entered fields; real fetching goes through the `VideoMetadataProvider` interface and is a future adapter. The URL input still validates and extracts the video ID locally.
- **Concurrency:** analysis runs in a `QThread` worker; progress and results flow through Qt signals; cancel via a cooperative flag checked between steps.
- **Secrets:** read only from environment variables or a local `.env` (via a small loader, no hardcoded keys). The Settings screen shows future API fields as disabled placeholders.
- **Paths:** `platformdirs` for `%LOCALAPPDATA%\YouTubeFactory` (DB, settings, logs). All file I/O uses `pathlib` with UTF-8 (`utf-8-sig` on read for BOM tolerance). Long-path support via the `\\?\` prefix helper and the app manifest `longPathAware`.
- **Temp files:** none created by the app. PyInstaller onefile extracts to `_MEI*` in `%TEMP%`, which the bootloader removes on exit; the plan notes this and tests clean shutdown. If onefile cleanup proves unreliable in verification, fallback is onedir zipped (decision deferred until tested on Windows).
- **High-DPI:** Qt6 default scaling with `PassThrough` rounding policy; fonts in pt, not px.
- **Taskbar identity:** `SetCurrentProcessExplicitAppUserModelID("YouTubeFactory.App")`, `.ico` embedded in the exe.
- **Logging:** `RotatingFileHandler` (1 MB x 3) in the user data dir.
- **Single instance:** local socket guard so a second launch focuses the first window.

## 2. File structure

```
youtube_factory/
├── pogoda-widget@example.com.zip        # PROTECTED, untouched
├── src/youtube_factory/
│   ├── __init__.py                      # __version__
│   ├── __main__.py                      # entry point
│   ├── app/                             # controllers, workers
│   │   ├── controller.py
│   │   └── workers.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── theme.py                     # dark/light/system QSS + tokens
│   │   ├── widgets/                     # toast, short_card, progress_steps, ...
│   │   └── views/                       # home, analysis, results, history, settings
│   ├── services/
│   │   ├── url_parser.py
│   │   ├── transcript_parser.py         # txt / srt / vtt
│   │   ├── analyzer.py                  # heuristic engine
│   │   ├── demo.py
│   │   └── exporter.py                  # JSON, CSV (UTF-8 BOM)
│   ├── data/
│   │   ├── paths.py
│   │   ├── db.py                        # schema + migrations
│   │   ├── repositories.py
│   │   ├── settings_store.py
│   │   └── logging_setup.py
│   ├── integrations/
│   │   ├── base.py                      # Protocols / ABCs
│   │   ├── youtube_api.py               # stub
│   │   ├── transcripts.py               # stub
│   │   └── llm.py                       # stub
│   ├── models.py                        # dataclasses
│   ├── strings_ru.py                    # all user-facing Russian strings
│   └── resources/                       # demo_transcript.json, fonts (if any)
├── assets/                              # icon.ico, icon.png, screenshots
├── scripts/
│   ├── build_exe.ps1
│   ├── make_icon.py
│   └── verify_protected_file.py
├── tests/
├── .github/workflows/build-release.yml
├── .env.example
├── .gitignore
├── BUILD.md
├── PLAN.md
├── README.md
├── LICENSE                              # MIT (proposed)
├── pyproject.toml
├── requirements.txt
└── youtube_factory.spec                 # PyInstaller spec
```

## 3. Data model

Dataclasses (`models.py`):

- `VideoInfo`: `video_id`, `url`, `title`, `channel`, `duration_sec`, `thumbnail_path|None`.
- `TranscriptSegment`: `start_sec`, `end_sec`, `text`.
- `Short`: `id`, `analysis_id`, `start_sec`, `end_sec`, `hook`, `title`, `description`, `hashtags: list[str]`, `score: int (0-100)`, `reason`, `is_favorite`, `is_edited`.
- `Analysis`: `id`, `created_at`, `mode` (`demo` | `manual`), `video: VideoInfo`, `shorts: list[Short]`.

SQLite schema (`PRAGMA user_version` migrations, foreign keys on):

```sql
analyses(id INTEGER PK, created_at TEXT, mode TEXT, video_id TEXT, url TEXT,
         title TEXT, channel TEXT, duration_sec INTEGER, thumbnail BLOB NULL);
shorts(id INTEGER PK, analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
       start_sec REAL, end_sec REAL, hook TEXT, title TEXT, description TEXT,
       hashtags TEXT /* JSON array */, score INTEGER CHECK(score BETWEEN 0 AND 100),
       reason TEXT, is_favorite INTEGER DEFAULT 0, is_edited INTEGER DEFAULT 0,
       position INTEGER);
```

Settings: JSON file in user data dir (`theme`, `export_dir`, window geometry, future API fields). Keys never written to it unless the user enters them in a future version, and then via Windows Credential Locker (`keyring`), not plain JSON.

## 4. UI screens (all visible text in Russian)

Shell: frameless-looking but native window chrome kept for correct snap/resize/maximize behavior on Windows 11; left navigation rail (Главная, История, Настройки) plus content stack. Dark default: bg `#0A0A0B`, surface `#141416`, accent `#7C5CFF`, score accent amber `#FFB020`. Subtle fade/slide transitions via `QPropertyAnimation`.

1. **Главная** — title «Фабрика Shorts», value proposition, large URL field, «Создать Shorts», «Попробовать пример», «Вставить транскрипт» (opens a dialog for paste or file), recent analyses list.
2. **Анализ** — five-step progress list («Получаем данные видео» → «Готовим результаты»), cancel button, inline Russian error panel with retry.
3. **Результаты** — video header (title, channel, duration, thumbnail, «Открыть на YouTube»), toolbar (избранное filter, экспорт JSON/CSV, «Новый анализ»), responsive card grid; each card: time range, hook, title, description, hashtags, score badge, reason, actions (копировать, редактировать, избранное, удалить), toasts.
4. **История** — list of analyses, open, delete with confirmation dialog.
5. **Настройки** — theme (тёмная / светлая / системная), export folder, disabled future API section, «О программе» with version.

## 5. Tests and quality

- `pytest`: URL parsing (watch, youtu.be, shorts, embed, bad input), SRT/VTT/TXT parsing incl. BOM, Cyrillic, malformed timestamps, analyzer determinism and 5–10 result bound, non-overlap, score range, exporter (CSV BOM, JSON round-trip), repositories on a temp DB, settings store.
- `pytest-qt` smoke tests run with `QT_QPA_PLATFORM=offscreen`: window creates, views switch, demo flow end to end.
- `ruff check` and `ruff format --check`.
- Limitation: this workspace is Linux. I can run unit and offscreen-Qt tests here, but **cannot build or launch a Windows `.exe` here**. The Windows build runs on GitHub Actions (`windows-latest`); the launch smoke test is a CI step (start exe with a `--smoke-test` flag that creates the window, runs the demo analysis, exits 0). Visual check on real Windows 11 remains with you.

## 6. Build and release plan

- PyInstaller: `--onefile --windowed`, name `YouTubeFactory`, icon `assets/icon.ico`, version resource, `--collect-data` only for our resources; the protected zip is never added.
- CI workflow `.github/workflows/build-release.yml`:
  1. Triggers: push to `main`, tags `v*.*.*`.
  2. `windows-latest`, Python 3.11, pip cache.
  3. Install `requirements.txt` + dev deps.
  4. Run `scripts/verify_protected_file.py` (fails if blob hash differs).
  5. `ruff`, `pytest`.
  6. Build exe; rename to `YouTubeFactory-<tag>-windows-x64.exe`; run `--smoke-test`.
  7. Upload as workflow artifact on every run.
  8. On tag push only: create GitHub Release and attach the exe (`softprops/action-gh-release`, `permissions: contents: write`).
- Release `v0.1.0`: I prepare the title, Russian notes and file list and show them to you. **I do not create the tag or release until you confirm.** Pushing the tag is what triggers publication, so tagging is gated on your approval too.
- Git access: this session currently has read-only access to the repo. To push commits I need push access attached (a separate approval step); otherwise I give you the exact `git` commands to run locally.

## 7. Delivery in stages (small parts)

1. Skeleton: `pyproject`, `requirements`, `.gitignore`, `models`, `paths`, logging, entry point, strings.
2. Services: URL parser, transcript parsers, analyzer, demo data, exporter + tests.
3. Data layer: SQLite, repositories, settings + tests.
4. UI: theme, shell, Главная, Анализ, workers.
5. UI: Результаты, История, Настройки, toasts.
6. Packaging: spec, icon, build script, `BUILD.md`, `README.md`, `.env.example`, `LICENSE`.
7. CI workflow, protected-file check, release draft for review.

## 8. Open questions

1. Replace the 9-byte placeholder `README.md` with the real one? (Proposed: yes.)
2. License: MIT OK? (Proposed default.)
3. Grant push access for the repo, or do you prefer to run git commands locally?
4. Thumbnails in v0.1.0 are demo or placeholder only, since the app makes no network calls yet. OK?
