# AHS Diagnostic Parser

Local-first, offline tool to parse HPE iLO AHS bundles (.ahs/.zip) and produce Markdown/JSON reports.
The parser understands BlackBox (`.bb`) payloads and highlights system-board faults when enabled.

## CLI Quickstart (Windows PowerShell)
```
git clone https://github.com/dillondenisburke-alt/Parser_Tool.git
cd Parser_Tool
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m ahsdp.cli --in .\tests\fixtures\demo_data\demo.ahs.zip --out .\exports\report.md --export .\exports
```

## Desktop Drop-Zone App
- Optional drag-and-drop support uses `tkinterdnd2` (`python -m pip install "ahsdp[gui]"`).
- Launch with `python -m ahsdp.gui` or the installed `ahsdp-gui` shortcut.
- Drop an `.ahs`/`.zip` bundle or click **Browse…**; outputs land in the chosen directory with JSON exports in `exports/`.

## Feature Toggles
Set any of these before running the CLI or GUI to opt into extra analysis:
- `AHS_BB=1` — enable `.bb` ingestion (zip/gzip/plain text BlackBox streams).
- `AHS_FAULTS=1` — turn on heuristic fault detection (system-board anomaly patterns).
- `AHS_KEEP_TMP=1` — preserve the temporary extraction directory for manual inspection.

## Packaging & Installation
- Repository: `https://github.com/dillondenisburke-alt/Parser_Tool.git`
- Editable install for development: `python -m pip install -e .`
- Standard install: `python -m pip install .`
- Entry points registered:
  - `ahsdp` (CLI at `ahsdp.cli:main`)
  - `ahsdp-gui` (desktop launcher at `ahsdp.gui:main`)

## Windows Bundle (PyInstaller)
- Install build deps: `python -m pip install .[gui] pyinstaller`
- Generate the executable: `powershell -File .\bin\build_gui.ps1 -Clean`
- The drop-zone binary appears under `dist\ahsdp_gui\ahsdp-gui.exe`, alongside README/license copies.
