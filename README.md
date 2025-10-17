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

## Cross-platform GUI Quickstart
Install the GUI extras and launch the desktop interface:

```
python -m pip install --upgrade --extra-index-url https://PySimpleGUI.net/install PySimpleGUI
python -m pip install "ahsdp[gui]"
python run_app.py  # or: python -m ahsdp.gui
```

The GUI extra declared in `pyproject.toml` pins `PySimpleGUI>=4.60.5`; installing from the
[official index mirror](https://PySimpleGUI.net/install) ensures you receive the maintained
build before launching the app.

The PySimpleGUI front-end lets you:

- Browse to an `.ahs`/`.zip` bundle or an extracted folder.
- Choose where the Markdown report is written (folder or `.md` path).
- Toggle `.bb` parsing, heuristic fault detection, and temporary extraction retention.
- Generate optional JSON exports alongside the report.
- Open the resulting report or export directory directly from the GUI.

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

## Windows Bundles (PyInstaller)
- Install build deps: `python -m pip install --upgrade --extra-index-url https://PySimpleGUI.net/install PySimpleGUI`
- Install build deps: `python -m pip install .[gui] pyinstaller`
- GUI build: `powershell -File .\bin\build_gui.ps1 -Clean`
- The drop-zone binary appears under `dist\ahsdp_gui\ahsdp-gui.exe`, alongside README/license copies.

### Portable CLI Executable
- Create/activate the PowerShell session and allow the script to run:
  ```
  Set-ExecutionPolicy -Scope Process Bypass -Force
  .\bin\build_cli.ps1 -Clean -Icon assets\icon.ico
  ```
  (If this is the first run, the script creates `.venv`, upgrades `pip`, installs requirements, and pulls in PyInstaller automatically.)
- When the build completes, the CLI binary lives at `dist\ahsdp.exe`.
- Smoke test:
  ```
  .\dist\ahsdp.exe --help
  .\dist\ahsdp.exe --input "C:\path\to\bundle_or_folder" --out .\exports
  ```
  Adjust `bin\build_cli.ps1` if you need to bundle extra data assets (see the commented `--add-data` examples inside the script).
