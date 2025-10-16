param(
  [string]$Python = "python",
  [switch]$Clean
)

Write-Host "== AHS Diagnostic Parser – Build (CLI + GUI) =="

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
Set-Location $repo

if ($Clean) {
  Write-Host "Cleaning build/dist..."
  Remove-Item -Recurse -Force .\build,.\dist -ErrorAction SilentlyContinue
}

# Ensure venv
if (-not (Test-Path ".\.venv")) {
  & $Python -m venv .venv
}
$venvPy = ".\.venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip setuptools wheel

# Dependencies (CLI + GUI)
@"
PySimpleGUI>=4.60
"@ | Set-Content -Encoding UTF8 .\requirements.gui.txt

# If you also have a base requirements.txt, install it first (ignore if missing)
if (Test-Path .\requirements.txt) {
  & $venvPy -m pip install -r .\requirements.txt
}

& $venvPy -m pip install -r .\requirements.gui.txt
& $venvPy -m pip install --upgrade pyinstaller

# Smoke tests
Write-Host "Smoke test: python -m src.ahsdp.cli --help"
& $venvPy -m src.ahsdp.cli --help | Out-Null

Write-Host "Smoke test: import GUI"
& $venvPy - << 'PY'
import ahsdp.gui as g
print("GUI import ok, version:", getattr(g, "VERSION", "?"))
PY

# Build CLI
pyinstaller --noconfirm --onefile --name ahsdp --console `
  --paths .\src `
  --hidden-import ahsdp.cli `
  .\bin\ahsdp_runner.py

# Build GUI
pyinstaller --noconfirm --onefile --name ahsdp_gui --windowed `
  --paths .\src `
  --hidden-import ahsdp.gui `
  .\bin\ahsdp_gui_runner.py

Write-Host ""
Write-Host "✅ Build complete:"
Write-Host "   $(Join-Path $repo 'dist\ahsdp.exe')"
Write-Host "   $(Join-Path $repo 'dist\ahsdp_gui.exe')"
