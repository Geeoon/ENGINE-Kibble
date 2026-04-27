#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

# Find whichever Python executable is available on this machine
$PythonExe = $null
foreach ($cmd in @("py", "python3", "python")) {
    & $cmd --version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $PythonExe = $cmd; break }
}

# Stops if calling python fails
if (-not $PythonExe) {
    Write-Error "Python not found. Install it from https://python.org and ensure it is added to PATH."
    exit 1
}

function Run-Python {
    & $PythonExe @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$InstallDir = "C:\Program Files\Kibble\edge_agent"
$LogDir = "C:\ProgramData\Kibble\logs"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create install and log directories if they don't already exist
New-Item -ItemType Directory -Force -Path $InstallDir, $LogDir | Out-Null

Run-Python -m pip install -r "$ScriptDir\requirements-windows.txt"

# Copy collector scripts into the install directory
Copy-Item "$ScriptDir\..\telemetry_collector.py" $InstallDir -Force
Copy-Item "$ScriptDir\windows_service.py" $InstallDir -Force
Copy-Item "$ScriptDir\..\collectors" $InstallDir -Recurse -Force

# Register and start the Windows service from the install directory
Push-Location $InstallDir
Run-Python windows_service.py install
Run-Python windows_service.py start
Pop-Location

Write-Host "Kibble Telemetry Collection Installation Complete: Check status with: Get-Service KibbleTelemetry"
