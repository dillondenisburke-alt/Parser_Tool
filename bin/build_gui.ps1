#requires -Version 5
[CmdletBinding()]
param(
    [string]$Spec = "$PSScriptRoot\ahsdp_gui.spec",
    [string]$Dist = "$PSScriptRoot\..\dist",
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "Building AHS Diagnostic Parser GUI..."

if ($Clean -and (Test-Path $Dist)) {
    Write-Host "Removing previous dist: $Dist"
    Remove-Item -Recurse -Force $Dist
}

$pyInstallerArgs = @(
    '--noconfirm',
    '--clean',
    "--distpath=$Dist",
    $Spec
)

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

& $pythonExe -m PyInstaller @pyInstallerArgs

$extras = @('README.md', 'LICENSE.txt')
foreach ($file in $extras) {
    $source = Join-Path $PSScriptRoot "..\$file"
    if (Test-Path $source) {
        Copy-Item $source -Destination $Dist -Force
    }
}

Write-Host "Build complete. Output located in $Dist"
