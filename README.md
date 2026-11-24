# YouTube Factory — Фабрика Shorts

Настольное приложение для Windows 11, которое превращает длинное YouTube-видео в готовые идеи для Shorts: с таймкодами, хуком, названием, описанием, хэштегами и оценкой вирального потенциала.

Всё работает локально на вашем компьютере. Python, Node.js и права администратора не нужны.

## Возможности

- Для каждого Short: диапазон времени («02:14 – 03:02»), хук, название, описание, хэштеги, потенциал от 0 до 100 и объяснение, почему момент может сработать.
- **Демо-режим.** Встроенный русскоязычный пример, работает полностью офлайн.
- **Свой транскрипт.** Вставьте текст или откройте файл `.txt`, `.srt` или `.vtt`. Анализ выполняется локально, без внешних ИИ-сервисов и ключей.
- Карточки можно редактировать, копировать, добавлять в избранное и удалять.
- Экспорт в JSON и CSV (CSV в UTF-8 с BOM, открывается в Excel без «кракозябр»). Экспортируются отмеченные карточки, а если ничего не отмечено — все.
- История анализов хранится локально, её можно открыть или удалить.
- Тёмная, светлая и системная темы.

## Скачать и установить

1. Откройте страницу [Releases](https://github.com/gamerfashpro-sudo/youtube_factory/releases).
2. Скачайте файл `YouTubeFactory-v0.1.0-windows-x64.exe`.
3. Запустите его двойным щелчком. Установка не нужна.

Файл пока не имеет цифровой подписи, поэтому Windows SmartScreen может показать предупреждение «Windows защитила ваш компьютер». Нажмите «Подробнее», затем «Выполнить в любом случае». Контрольную сумму SHA-256 можно сверить с указанной в описании релиза.

Данные (история, настройки, журнал) хранятся в `%LOCALAPPDATA%\YouTubeFactory`. Чтобы удалить всё, закройте приложение, удалите exe-файл и эту папку.

## Как пользоваться

1. Нажмите «Попробовать пример», чтобы увидеть результат на встроенном видео.
2. Для своего видео вставьте ссылку и нажмите «Вставить транскрипт…». Добавьте текст или файл с субтитрами.
3. Автоматическое получение транскрипта по ссылке появится в следующих версиях.

---

## Run from source

Requirements: Windows 11 x64 (or Linux/macOS for development), Python 3.11+.

```powershell
git clone https://github.com/gamerfashpro-sudo/youtube_factory.git
cd youtube_factory
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pip install -e .
python -m youtube_factory
```

Run the checks:

```powershell
ruff check .
pytest -q
```

UI tests run headless. On Linux set `QT_QPA_PLATFORM=offscreen` (the test suite does this itself).

## Build the .exe locally

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

The script lints, tests, builds with PyInstaller, runs a smoke test and writes `dist\YouTubeFactory-v<version>-windows-x64.exe`. See [BUILD.md](BUILD.md) for details.

## Environment variables

Version 0.1.0 makes no network requests and needs no keys. The variables below are reserved for future integrations. Secrets are read only from Windows environment variables or a local `.env` file, never from the source code. See [.env.example](.env.example).

| Variable | Purpose |
| --- | --- |
| `YOUTUBE_API_KEY` | YouTube Data API (video metadata) |
| `TRANSCRIPT_PROVIDER`, `TRANSCRIPT_API_KEY` | Transcript extraction service |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Local or cloud language model |
| `YOUTUBE_FACTORY_DATA_DIR` | Override the user data directory (mainly for tests) |

## Roadmap

- 0.2: video metadata and thumbnail via the YouTube Data API.
- 0.3: automatic transcript retrieval.
- 0.4: refining Shorts with a local or cloud LLM.
- Later: code signing, installer, update check.

## License

[MIT](LICENSE)
