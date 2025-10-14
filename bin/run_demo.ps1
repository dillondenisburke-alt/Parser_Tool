param(
  [string]$InputDir = ".\tests\fixtures\demo_data",
  [string]$OutDir   = ".\exports"
)

# Ensure output folder
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Count demo AHS files
$files = Get-ChildItem -Path $InputDir -Filter *.ahs -ErrorAction SilentlyContinue
$cnt = ($files | Measure-Object).Count

# Build a simple report
$report = @"
# AHS Diagnostic Parser — Demo Report

Scanned folder: $((Resolve-Path $InputDir).Path)
Files matched (*.ahs): $cnt

Files:
$($files | ForEach-Object { " - " + $_.Name } | Out-String)

Generated: $(Get-Date -Format s)
"@

$reportPath = Join-Path $OutDir "report.md"
$report | Set-Content -Encoding UTF8 $reportPath

Write-Host "✅ Report written to $reportPath"
