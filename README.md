# AHS Diagnostic Parser

Local-first, offline tool to parse HPE iLO AHS bundles (.ahs/.zip) and produce a Markdown report and JSON exports.
The parser now understands core BlackBox (`.bb`) payloads and surfaces common system-board faults when enabled.

## Quickstart (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
\ = ".\src"
python -m ahsdp.cli --in .\tests\fixtures\demo_data\demo.ahs.zip --out .\exports\report.md --export .\exports

## Feature toggles

Set the following environment variables before running the CLI to opt into additional analysis:

- `AHS_BB=1` — enable `.bb` ingestion (zip/gzip/plain text BlackBox streams).
- `AHS_FAULTS=1` — turn on heuristic fault detection (system-board anomaly patterns).
- `AHS_KEEP_TMP=1` — preserve the temporary extraction directory for manual inspection.
