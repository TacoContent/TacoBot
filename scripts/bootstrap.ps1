<#!
.SYNOPSIS
    Bootstrap TacoBot development environment (Windows PowerShell).
.DESCRIPTION
    Creates a local virtual environment (.venv), upgrades pip, installs runtime
    dependencies (editable), and optionally dev/test tools.
.PARAMETER Dev
    Switch to also install [dev] optional dependencies.
.EXAMPLE
    ./scripts/bootstrap.ps1
.EXAMPLE
    ./scripts/bootstrap.ps1 -Dev
#>
param(
    [switch]$Dev
)

$ErrorActionPreference = 'Stop'

Write-Host '[tacobot] Creating virtual environment (.venv)...'
if (-not (Test-Path .venv)) {
    python -m venv .venv
} else {
    Write-Host '[tacobot] Virtual environment already exists, skipping creation.'
}

Write-Host '[tacobot] Activating virtual environment'
. .\.venv\Scripts\Activate.ps1

Write-Host '[tacobot] Upgrading pip'
python -m pip install --upgrade pip wheel setuptools

Write-Host '[tacobot] Installing project (editable)'
if ($Dev) {
    pip install -e .[dev,docs]
} else {
    pip install -e .
}

Write-Host '[tacobot] Done.'
