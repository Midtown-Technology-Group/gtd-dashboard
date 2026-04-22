#!/usr/bin/env pwsh
<#
.SYNOPSIS
    GTD Dashboard CLI PowerShell Wrapper

.DESCRIPTION
    Wrapper script to invoke the GTD Dashboard CLI with proper Python environment detection.
    Auto-discovers the project and runs the CLI from the correct location.

.EXAMPLE
    .\invoke.ps1 now
    Show all NOW/DOING tasks

.EXAMPLE
    .\invoke.ps1 waiting --with-m365
    Show WAITING-FOR tasks with M365 context

.EXAMPLE
    .\invoke.ps1 all --format json
    Export all tasks to JSON
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

# Determine script location and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

$ProjectRoot = Resolve-Path (Join-Path $ScriptDir ".")

# Try to find Python
function Find-Python {
    $candidates = @(
        "python"
        "python3"
        "py"
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    
    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }
    
    return $null
}

# Check for virtual environment
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = Find-Python
}

if (-not $Python) {
    Write-Error "Python not found. Please install Python 3.10+ and ensure it's in your PATH."
    exit 1
}

# Check Python version
$PythonVersion = & $Python --version 2>&1
Write-Host "Using: $PythonVersion" -ForegroundColor DarkGray

# Check if package is installed, otherwise use local source
$PackageCheck = & $Python -c "import gtd_dashboard; print('installed')" 2>&1
if ($LASTEXITCODE -ne 0 -or $PackageCheck -ne "installed") {
    # Run from source
    $SourceDir = Join-Path $ProjectRoot "src"
    $Env:PYTHONPATH = "$SourceDir;$Env:PYTHONPATH"
    $CliModule = "gtd_dashboard.cli"
    
    Write-Host "Running from source: $SourceDir" -ForegroundColor DarkGray
    & $Python -m $CliModule @Arguments
} else {
    # Run installed package
    Write-Host "Running installed package" -ForegroundColor DarkGray
    & $Python -m gtd_dashboard.cli @Arguments
}

exit $LASTEXITCODE
