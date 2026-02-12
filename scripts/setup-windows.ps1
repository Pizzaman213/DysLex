# ============================================================================
# DysLex AI — Windows Setup Script
# ============================================================================
# Downloads and installs all prerequisites, then launches DysLex AI.
#
# Usage (run in PowerShell as Administrator):
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\scripts\setup-windows.ps1
#
# What this script does:
#   1. Installs Chocolatey package manager (if missing)
#   2. Installs Python 3.12, Node.js 20, PostgreSQL 15, Redis
#   3. Starts PostgreSQL and Redis services
#   4. Creates the PostgreSQL database and user
#   5. Sets up the backend virtual environment + installs dependencies
#   6. Installs frontend npm dependencies
#   7. Creates a .env file from the template
#   8. Launches DysLex AI via run.py
# ============================================================================

$ErrorActionPreference = "Stop"

# --- Colors ---------------------------------------------------------------
function Write-Info    { param($msg) Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Write-Ok      { param($msg) Write-Host "[  ok]  $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Write-Fail    { param($msg) Write-Host "[fail]  $msg" -ForegroundColor Red }

# --- Check Admin ----------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Fail "This script must be run as Administrator."
    Write-Host ""
    Write-Host "  Right-click PowerShell -> 'Run as Administrator', then re-run this script." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# --- Banner ---------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DysLex AI - Windows Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Detect project root --------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot
Write-Info "Project root: $ProjectRoot"

# --- 1. Chocolatey --------------------------------------------------------
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Info "Installing Chocolatey package manager..."
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Ok "Chocolatey installed"
} else {
    Write-Ok "Chocolatey already installed"
}

# --- Helper: refresh PATH after installs ---------------------------------
function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- 2. Python 3.11+ ------------------------------------------------------
$needPython = $true
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($pyVer) {
        $parts = $pyVer.Split('.')
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -ge 3 -and $minor -ge 11) {
            $needPython = $false
            Write-Ok "Python $pyVer found (3.11+ required)"
        }
    }
}

if ($needPython) {
    Write-Info "Installing Python 3.12..."
    choco install python312 -y --no-progress
    Refresh-Path
    Write-Ok "Python 3.12 installed"
}

# --- 3. Node.js 20+ -------------------------------------------------------
$needNode = $true
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = (node --version) -replace 'v', ''
    $nodeMajor = [int]($nodeVer.Split('.')[0])
    if ($nodeMajor -ge 20) {
        $needNode = $false
        Write-Ok "Node.js v$nodeVer found (v20+ required)"
    }
}

if ($needNode) {
    Write-Info "Installing Node.js 20..."
    choco install nodejs-lts -y --no-progress
    Refresh-Path
    Write-Ok "Node.js installed"
}

# --- 4. PostgreSQL ---------------------------------------------------------
$pgInstalled = (Get-Command psql -ErrorAction SilentlyContinue) -or (Test-Path "C:\Program Files\PostgreSQL")
if (-not $pgInstalled) {
    Write-Info "Installing PostgreSQL 15..."
    choco install postgresql15 --params "/Password:postgres" -y --no-progress
    Refresh-Path
    Write-Ok "PostgreSQL 15 installed"
} else {
    Write-Ok "PostgreSQL already installed"
}

# Ensure PostgreSQL service is running
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService) {
    if ($pgService.Status -ne 'Running') {
        Write-Info "Starting PostgreSQL service..."
        Start-Service $pgService.Name
        Start-Sleep -Seconds 3
        Write-Ok "PostgreSQL started"
    } else {
        Write-Ok "PostgreSQL is running"
    }
} else {
    Write-Warn "PostgreSQL service not found — you may need to start it manually"
}

# Create database and user
Write-Info "Setting up database..."

# Find psql.exe
$psqlPath = "psql"
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    $pgDir = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($pgDir) {
        $psqlPath = Join-Path $pgDir.FullName "bin\psql.exe"
        $env:Path += ";$(Join-Path $pgDir.FullName 'bin')"
    }
}

try {
    & $psqlPath -U postgres -c "CREATE USER dyslex WITH PASSWORD 'dyslex';" 2>$null
} catch { }
try {
    & $psqlPath -U postgres -c "CREATE DATABASE dyslex OWNER dyslex;" 2>$null
} catch { }
try {
    & $psqlPath -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE dyslex TO dyslex;" 2>$null
} catch { }
Write-Ok "Database 'dyslex' ready"

# --- 5. Redis --------------------------------------------------------------
$redisInstalled = Get-Command redis-server -ErrorAction SilentlyContinue
if (-not $redisInstalled) {
    Write-Info "Installing Redis..."
    choco install redis-64 -y --no-progress 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Fallback: Memurai (Redis-compatible for Windows)
        Write-Info "Trying Memurai (Redis-compatible)..."
        choco install memurai-developer -y --no-progress 2>$null
    }
    Refresh-Path
    Write-Ok "Redis installed"
} else {
    Write-Ok "Redis already installed"
}

# Start Redis service
$redisService = Get-Service -Name "redis*" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $redisService) {
    $redisService = Get-Service -Name "memurai*" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($redisService -and $redisService.Status -ne 'Running') {
    Write-Info "Starting Redis..."
    Start-Service $redisService.Name
    Start-Sleep -Seconds 2
    Write-Ok "Redis started"
} elseif ($redisService) {
    Write-Ok "Redis is running"
} else {
    Write-Warn "Redis service not found — it is optional but recommended"
}

# --- 6. Backend setup ------------------------------------------------------
Write-Info "Setting up backend..."
Set-Location "$ProjectRoot\backend"

if (-not (Test-Path "venv")) {
    Write-Info "Creating Python virtual environment..."
    python -m venv venv
}

# Activate and install
Write-Info "Installing backend dependencies (this may take a few minutes)..."
& ".\venv\Scripts\pip.exe" install --upgrade pip -q
& ".\venv\Scripts\pip.exe" install -r requirements.txt -q
Write-Ok "Backend dependencies installed"

# --- 7. Frontend setup -----------------------------------------------------
Write-Info "Setting up frontend..."
Set-Location "$ProjectRoot\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Info "Installing frontend dependencies..."
    npm install
} else {
    Write-Ok "Frontend node_modules already present"
}
Write-Ok "Frontend dependencies installed"

# --- 8. Environment file ---------------------------------------------------
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    Write-Info "Creating .env file..."
    @"
# DysLex AI Environment Configuration
# Get your API key at: https://build.nvidia.com
NVIDIA_NIM_API_KEY=

# Database (defaults work with local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=change-me-in-production
"@ | Set-Content -Path ".env" -Encoding UTF8
    Write-Ok ".env created - edit it to add your NVIDIA_NIM_API_KEY"
} else {
    Write-Ok ".env already exists"
}

# --- Done! -----------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To start DysLex AI, run:" -ForegroundColor White
Write-Host ""
Write-Host "    python run.py --auto-setup --no-https" -ForegroundColor White -NoNewline
Write-Host ""
Write-Host ""
Write-Host "  For HTTPS (recommended), first generate dev certificates:" -ForegroundColor White
Write-Host ""
Write-Host "    bash scripts/generate-dev-certs.sh" -ForegroundColor White
Write-Host "    python run.py --auto-setup" -ForegroundColor White
Write-Host ""

# Ask if user wants to start now
$startNow = Read-Host "Start DysLex AI now? [Y/n]"
if ([string]::IsNullOrWhiteSpace($startNow) -or $startNow -match '^[Yy]') {
    Write-Host ""
    python run.py --auto-setup --no-https
}
