# Building YouTube Factory on Windows 11

Target: `YouTubeFactory-v<version>-windows-x64.exe`, a single windowed executable built with PyInstaller. It runs from a normal user account and needs no installer.

## Prerequisites

- Windows 11 x64
- Python 3.11 or newer (64-bit) from python.org, with "Add python.exe to PATH" ticked
- Git

Verify:

```powershell
python --version
python -c "import struct; print(struct.calcsize('P') * 8)"   # must print 64
```

## One-command build

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

Add `-SkipTests` to skip linting and tests. The script:

1. Verifies the protected file `pogoda-widget@example.com.zip` is unchanged.
2. Creates `.venv` and installs `requirements-dev.txt`.
3. Runs `ruff` and `pytest`.
4. Builds with `youtube_factory.spec`.
5. Copies the result to `dist\YouTubeFactory-v<version>-windows-x64.exe`.
6. Runs `--smoke-test`: starts the exe, runs the demo analysis in a temporary data directory, exits with code 0 on success.
7. Prints the SHA-256 hash.

## Manual build

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pyinstaller youtube_factory.spec --noconfirm --clean
dist\YouTubeFactory.exe --smoke-test
echo $LASTEXITCODE
```

## What the spec does

- Entry point `scripts\entry.py`, sources from `src\`.
- Bundles `src\youtube_factory\resources` (icon).
- Excludes unused Qt modules to reduce size.
- Embeds `assets\icon.ico`, version info (`assets\version_info.txt`) and `assets\app.manifest`.
- The manifest requests `asInvoker` (no administrator rights), enables long paths and a UTF-8 active code page.
- High DPI is handled by Qt with the `PassThrough` rounding policy.
- The taskbar identity is set with `SetCurrentProcessExplicitAppUserModelID("YouTubeFactory.App")`.

## Temporary files

A single-file PyInstaller executable unpacks itself to `%TEMP%\_MEI*` and removes that folder on normal exit. If the process is killed, Windows may leave the folder behind; it is safe to delete. The application itself writes no temporary files. `--smoke-test` uses a temporary data directory and deletes it.

## Updating the icon

```powershell
pip install pillow
python scripts\make_icon.py
```

## Release via GitHub Actions

Pushing a tag such as `v0.2.0` runs `.github\workflows\build-release.yml`, which builds the exe and attaches it to a GitHub Release. The tag must match `__version__` in `src\youtube_factory\__init__.py`, otherwise the workflow fails.

## Runtime tools

ffmpeg and Deno are **not** bundled, which keeps the exe small and fast to start. On first use `services/tools.py` downloads pinned PyPI wheels (`imageio-ffmpeg`, `deno`), checks their SHA-256 and unpacks the binaries into `%LOCALAPPDATA%\YouTubeFactory\tools`. To bump a tool, update the version, URL and hash in `TOOLS` there. `imageio-ffmpeg` is a dev dependency only, so tests can cut real video.

## Troubleshooting

- **SmartScreen warning:** the exe is unsigned. Click "More info", then "Run anyway".
- **Antivirus false positive:** common for unsigned PyInstaller one-file builds. Report it to the vendor, or build from source.
- **`ModuleNotFoundError` at start:** rebuild with `--clean`; check `build\youtube_factory\warn-youtube_factory.txt`.
- **Logs:** `%LOCALAPPDATA%\YouTubeFactory\logs\youtube_factory.log`.
