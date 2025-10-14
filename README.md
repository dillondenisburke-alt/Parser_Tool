# AHS Diagnostic Parser

Local-first, offline tool to parse HPE iLO AHS bundles (.ahs/.zip) and produce Markdown/JSON reports.
The parser understands BlackBox (`.bb`) payloads and highlights system-board faults when enabled.

## CLI Quickstart (Windows PowerShell)
```
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

## Hardware Fault Summary
- The Markdown report starts with a **Hardware Fault Summary** that groups findings by hardware component and lists the highest severity/count detected for each area.
- Components with findings show emoji-coded status (`🔴` error, `🟠` warning, `🟢` clear). Components without telemetry are called out as `⚪ … / data missing` so operators know coverage gaps.
- BlackBox parsing (`AHS_BB`) and fault heuristics (`AHS_FAULTS`) must both be enabled to receive system-board coverage. Disabling either flag, or supplying bundles without `.bb` logs, will mark the affected components as “data missing”.
- JSON exports now expose a `component_matrix` field inside `metadata.json`, e.g. `{"System Board": {"status": "warn"}, "Power Supply": {"status": "missing"}}`, so automation can reason about the same component health matrix shown in the Markdown report.
- Treat “data missing” as “no conclusion”: it reflects absent telemetry rather than a clean bill of health and should prompt collection of fresh diagnostics before closing an investigation.

## Packaging & Installation
- Editable install for development: `python -m pip install -e .`
- Standard install: `python -m pip install .`
- Entry points registered:
  - `ahsdp` (CLI at `ahsdp.cli:main`)
  - `ahsdp-gui` (desktop launcher at `ahsdp.gui:main`)

## Windows Bundle (PyInstaller)
- Install build deps: `python -m pip install .[gui] pyinstaller`
- Generate the executable: `powershell -File .\bin\build_gui.ps1 -Clean`
- The drop-zone binary appears under `dist\ahsdp_gui\ahsdp-gui.exe`, alongside README/license copies.
