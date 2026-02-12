# ============================================================================
# DysLex AI — Bootstrap Script (Windows)
# ============================================================================
# Minimal script that ensures Python 3.11+ is installed, then delegates
# everything else to run.py --auto-setup.
#
# Usage (run in PowerShell, preferably as Administrator):
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\scripts\bootstrap.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

function Write-Info    { param($msg) Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Write-Ok      { param($msg) Write-Host "[  ok]  $msg" -ForegroundColor Green }
function Write-Fail    { param($msg) Write-Host "[fail]  $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DysLex AI - Bootstrap" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Detect project root --------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

if (-not (Test-Path "run.py")) {
    Write-Fail "run.py not found in $ProjectRoot. Please run this script from the project root or scripts\ directory."
}

# --- Check Python 3.11+ ---------------------------------------------------
function Test-PythonOk {
    $pythonCmd = $null
    # Try python3 first, then python
    foreach ($cmd in @("python3", "python")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $pythonCmd = $cmd
            break
        }
    }
    if (-not $pythonCmd) { return $false }

    try {
        $ver = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver) {
            $parts = $ver.Split('.')
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            return ($major -ge 3 -and $minor -ge 11)
        }
    } catch { }
    return $false
}

if (-not (Test-PythonOk)) {
    Write-Info "Python 3.11+ not found. Installing..."

    # Check for Chocolatey
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Info "Installing Chocolatey package manager..."

        # Check admin
        $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not $isAdmin) {
            Write-Fail "Administrator privileges required to install Chocolatey. Right-click PowerShell -> 'Run as Administrator'."
        }

        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-Ok "Chocolatey installed"
    }

    Write-Info "Installing Python 3.12 via Chocolatey..."
    choco install python312 -y --no-progress
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Ok "Python 3.12 installed"

    if (-not (Test-PythonOk)) {
        Write-Fail "Python 3.11+ installation failed. Please install manually: https://python.org/downloads"
    }
} else {
    $pyCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
    $pyVer = & $pyCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Ok "Python $pyVer found"
}

# --- Hand off to run.py ---------------------------------------------------
Write-Info "Handing off to run.py --auto-setup..."
Write-Host ""

$pyCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $pyCmd run.py --auto-setup @args
