<#
.SYNOPSIS
  Builds YouTubeFactory-v<version>-windows-x64.exe on Windows 11 (x64).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1 -SkipTests
#>
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

Step "Checking that the protected repository file is untouched"
python scripts\verify_protected_file.py
if ($LASTEXITCODE -ne 0) { throw "Protected file check failed" }

Step "Creating virtual environment (.venv)"
if (-not (Test-Path .venv)) { python -m venv .venv }
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"

Step "Installing dependencies"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }

if (-not $SkipTests) {
    Step "Linting and testing"
    & $py -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "ruff failed" }
    $env:QT_QPA_PLATFORM = "offscreen"
    & $py -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    Remove-Item Env:\QT_QPA_PLATFORM
}

Step "Building the executable with PyInstaller"
& $py -m PyInstaller youtube_factory.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$version = (& $py -c "import sys; sys.path.insert(0, 'src'); from youtube_factory import __version__; print(__version__)").Trim()
$final = "dist\YouTubeFactory-v$version-windows-x64.exe"
Copy-Item dist\YouTubeFactory.exe $final -Force

Step "Smoke test (starts the exe, runs the demo analysis, exits)"
$proc = Start-Process -FilePath $final -ArgumentList "--smoke-test" -PassThru -Wait
if ($proc.ExitCode -ne 0) { throw "Smoke test failed with exit code $($proc.ExitCode)" }

Step "Done"
Get-Item $final | Format-List Name, Length
Get-FileHash $final -Algorithm SHA256 | Format-List Hash
