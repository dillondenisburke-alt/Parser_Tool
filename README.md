# AHS Diagnostic Parser

Local-first, offline tool to parse HPE iLO AHS bundles (.ahs/.zip) and produce a Markdown report and JSON exports.
MVP parses non-.bb artifacts only.

## Quickstart (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
\ = ".\src"
python -m ahsdp.cli --in .\tests\fixtures\demo_data\demo.ahs.zip --out .\exports\report.md --export .\exports
