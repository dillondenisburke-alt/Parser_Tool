param(
  [switch]$Clean,
  [string]$Icon = "assets\icon.ico"
)

$ErrorActionPreference = "Stop"

Write-Host "== AHS Diagnostic Parser – CLI Builder =="

# 0) Print where we are
Write-Host ("Repo root: " + (Resolve-Path ".").Path)

# 1) Ensure venv
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  Write-Host "Creating virtualenv..."
  py -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

# 2) Install deps
python -m pip install -U pip wheel setuptools
pip install -r requirements.txt
pip install pyinstaller

# 3) Optional clean
if ($Clean) {
  Write-Host "Cleaning build/dist..."
  if (Test-Path .\build) { Remove-Item .\build -Recurse -Force }
  if (Test-Path .\dist)  { Remove-Item .\dist  -Recurse -Force }
}

# 4) Verify the CLI imports (quick smoke)
Write-Host "Smoke test: python -m src.ahsdp.cli --help"
python -m src.ahsdp.cli --help | Out-Null

# 5) Prepare a tiny runner so PyInstaller has a plain script entry point
$runner = @"
from src.ahsdp.cli import main
if __name__ == "__main__":
    main()
"@
Set-Content -Encoding UTF8 .\bin\ahsdp_runner.py $runner

# 6) Build with PyInstaller
$iconPath = Resolve-Path $Icon -ErrorAction SilentlyContinue
if (-not $iconPath) {
  Write-Warning "Icon not found at '$Icon' – continuing without icon."
  $iconArg = @()
} else {
  $iconArg = @("--icon", $iconPath.Path)
}

# include templates or any data files here if you have them
# Example: --add-data "src\ahsdp\templates;ahsdp\templates"
$addData = @()

$pyiArgs = @(
  "--noconfirm",
  "--onefile",
  "--name", "ahsdp",
  "--console"
) + $iconArg + $addData + @(".\bin\ahsdp_runner.py")

Write-Host "Building EXE..."
pyinstaller @pyiArgs

# 7) Result
$exe = Join-Path ".\dist" "ahsdp.exe"
if (Test-Path $exe) {
  Write-Host ""
  Write-Host "✅ Build complete:"
  Write-Host "   $((Resolve-Path $exe).Path)"
} else {
  Write-Error "Build failed – ahsdp.exe not found in dist"
}
