#requires -Version 5
[CmdletBinding(DefaultParameterSetName = 'Default')]
param(
    [string]$Name = "AHS_Diagnostic_Parser",
    [string]$Icon = "",
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $repoRoot 'dist'
$buildDir = Join-Path $repoRoot 'build'
$specDir = Join-Path $repoRoot 'spec'

if ($Clean) {
    if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }
    if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
    if (Test-Path $specDir) { Remove-Item -Recurse -Force $specDir }
}

if ($env:VIRTUAL_ENV) {
    $pythonExe = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        $pythonExe = 'py'
    }
}

$pyInstallerArgs = @(
    '--name', $Name,
    '--onefile',
    '--noconfirm',
    '--console',
    '--paths', 'src',
    '--add-data', 'docs;docs',
    '--add-data', 'policy;policy',
    'ahsdp_app.py'
)

if ($Icon) {
    $pyInstallerArgs += @('--icon', $Icon)
}

& $pythonExe -m PyInstaller @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Executable produced at: dist\$Name.exe"
