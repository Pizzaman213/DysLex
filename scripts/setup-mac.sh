#!/usr/bin/env bash
# ============================================================================
# DysLex AI — macOS Setup Script
# ============================================================================
# Downloads and installs all prerequisites, then launches DysLex AI.
#
# Usage:
#   curl -fsSL <raw-url>/scripts/setup-mac.sh | bash
#   — or —
#   chmod +x scripts/setup-mac.sh && ./scripts/setup-mac.sh
#
# What this script does:
#   1. Installs Homebrew (if missing)
#   2. Installs Python 3.12, Node.js 20, PostgreSQL 15, Redis
#   3. Starts PostgreSQL and Redis services
#   4. Creates the PostgreSQL database and user
#   5. Sets up the backend virtual environment + installs dependencies
#   6. Installs frontend npm dependencies
#   7. Creates a .env file from the template
#   8. Launches DysLex AI via run.py
# ============================================================================

set -euo pipefail

# --- Colors ---------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[  ok]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[fail]${NC}  $*"; }

# --- Banner ---------------------------------------------------------------
echo ""
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo -e "${BOLD}${CYAN}  DysLex AI — macOS Setup${NC}"
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo ""

# --- Detect project root --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"
info "Project root: $PROJECT_ROOT"

# --- 1. Homebrew -----------------------------------------------------------
if ! command -v brew &>/dev/null; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    success "Homebrew installed"
else
    success "Homebrew already installed"
fi

# --- 2. Python 3.11+ ------------------------------------------------------
NEED_PYTHON=false
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 11) )); then
        NEED_PYTHON=true
    fi
else
    NEED_PYTHON=true
fi

if $NEED_PYTHON; then
    info "Installing Python 3.12..."
    brew install python@3.12
    success "Python 3.12 installed"
else
    success "Python $PY_VERSION found (3.11+ required)"
fi

# --- 3. Node.js 20+ -------------------------------------------------------
NEED_NODE=false
if command -v node &>/dev/null; then
    NODE_MAJOR=$(node --version | sed 's/v//' | cut -d. -f1)
    if (( NODE_MAJOR < 20 )); then
        NEED_NODE=true
    fi
else
    NEED_NODE=true
fi

if $NEED_NODE; then
    info "Installing Node.js 20..."
    brew install node@20
    brew link --overwrite node@20 2>/dev/null || true
    success "Node.js 20 installed"
else
    success "Node.js $(node --version) found (v20+ required)"
fi

# --- 4. PostgreSQL 15+ ----------------------------------------------------
if ! brew list postgresql@15 &>/dev/null && ! brew list postgresql@16 &>/dev/null && ! brew list postgresql@17 &>/dev/null; then
    info "Installing PostgreSQL 15..."
    brew install postgresql@15
    success "PostgreSQL 15 installed"
else
    success "PostgreSQL already installed"
fi

# Helper: check if PostgreSQL is accepting connections
pg_running() {
    # Try pg_isready first (may not be in PATH for brew installs)
    if command -v pg_isready &>/dev/null; then
        pg_isready -q 2>/dev/null && return 0
    fi
    # Try the brew-linked path
    local pg_bin
    for pg_bin in /opt/homebrew/opt/postgresql@1*/bin/pg_isready /usr/local/opt/postgresql@1*/bin/pg_isready; do
        if [[ -x "$pg_bin" ]]; then
            "$pg_bin" -q 2>/dev/null && return 0
        fi
    done
    # Fallback: simple TCP port check
    python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost',5432)); s.close()" 2>/dev/null
}

# Start PostgreSQL
if ! pg_running; then
    info "Starting PostgreSQL..."
    brew services start postgresql@15 2>/dev/null || brew services start postgresql@16 2>/dev/null || brew services start postgresql 2>/dev/null || true
    sleep 3
    if pg_running; then
        success "PostgreSQL started"
    else
        warn "PostgreSQL may not have started — run.py --auto-setup will retry"
    fi
else
    success "PostgreSQL is running"
fi

# Ensure PostgreSQL bin directory is in PATH for createuser/createdb/psql
for pg_dir in /opt/homebrew/opt/postgresql@1*/bin /usr/local/opt/postgresql@1*/bin; do
    if [[ -d "$pg_dir" ]]; then
        export PATH="$pg_dir:$PATH"
        break
    fi
done

# Create database and user (ignore errors if they already exist)
info "Setting up database..."
createuser dyslex 2>/dev/null || true
createdb -O dyslex dyslex 2>/dev/null || true
psql -d dyslex -c "ALTER USER dyslex WITH PASSWORD 'dyslex';" 2>/dev/null || true
success "Database 'dyslex' ready"

# --- 5. Redis --------------------------------------------------------------
if ! brew list redis &>/dev/null; then
    info "Installing Redis..."
    brew install redis
    success "Redis installed"
else
    success "Redis already installed"
fi

if ! redis-cli ping &>/dev/null 2>&1; then
    info "Starting Redis..."
    brew services start redis
    sleep 2
    success "Redis started"
else
    success "Redis is running"
fi

# --- 6. Backend setup ------------------------------------------------------
info "Setting up backend..."
cd "$PROJECT_ROOT/backend"

if [[ ! -d venv ]]; then
    info "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
info "Installing backend dependencies (this may take a few minutes)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
success "Backend dependencies installed"

# --- 7. Frontend setup -----------------------------------------------------
info "Setting up frontend..."
cd "$PROJECT_ROOT/frontend"

if [[ ! -d node_modules ]]; then
    info "Installing frontend dependencies..."
    npm install
else
    success "Frontend node_modules already present"
fi
success "Frontend dependencies installed"

# --- 8. Environment file ---------------------------------------------------
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
    info "Creating .env file..."
    cat > .env <<'ENVEOF'
# DysLex AI Environment Configuration
# Get your API key at: https://build.nvidia.com
NVIDIA_NIM_API_KEY=

# Database (defaults work with local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=change-me-in-production
ENVEOF
    success ".env created — edit it to add your NVIDIA_NIM_API_KEY"
else
    success ".env already exists"
fi

# --- Done! -----------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}============================================================${NC}"
echo -e "${BOLD}${GREEN}  Setup complete!${NC}"
echo -e "${BOLD}${GREEN}============================================================${NC}"
echo ""
echo -e "  To start DysLex AI, run:"
echo -e ""
echo -e "    ${BOLD}python3 run.py --auto-setup${NC}"
echo ""
echo -e "  Or to start now automatically:"
echo -e ""
echo -e "    ${BOLD}python3 run.py --auto-setup --no-https${NC}"
echo ""
echo -e "  For HTTPS (recommended), first generate dev certificates:"
echo -e ""
echo -e "    ${BOLD}bash scripts/generate-dev-certs.sh${NC}"
echo -e "    ${BOLD}python3 run.py --auto-setup${NC}"
echo ""

# Ask if user wants to start now
read -rp "Start DysLex AI now? [Y/n] " START_NOW
START_NOW=${START_NOW:-Y}
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    echo ""
    exec python3 run.py --auto-setup --no-https
fi
