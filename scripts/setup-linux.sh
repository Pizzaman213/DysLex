#!/usr/bin/env bash
# ============================================================================
# DysLex AI — Linux Setup Script
# ============================================================================
# Downloads and installs all prerequisites, then launches DysLex AI.
# Supports: Ubuntu/Debian, Fedora/RHEL, and Arch Linux.
#
# Usage:
#   curl -fsSL <raw-url>/scripts/setup-linux.sh | bash
#   — or —
#   chmod +x scripts/setup-linux.sh && ./scripts/setup-linux.sh
#
# What this script does:
#   1. Detects your Linux distribution
#   2. Installs Python 3.11+, Node.js 20+, PostgreSQL, Redis
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
NC='\033[0m'

info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[  ok]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[fail]${NC}  $*"; exit 1; }

# --- Banner ---------------------------------------------------------------
echo ""
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo -e "${BOLD}${CYAN}  DysLex AI — Linux Setup${NC}"
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo ""

# --- Detect project root --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"
info "Project root: $PROJECT_ROOT"

# --- Detect distro --------------------------------------------------------
DISTRO="unknown"
PKG=""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
        ubuntu|debian|pop|linuxmint|elementary|zorin)
            DISTRO="debian"
            PKG="apt"
            ;;
        fedora|rhel|centos|rocky|alma)
            DISTRO="fedora"
            PKG="dnf"
            ;;
        arch|manjaro|endeavouros)
            DISTRO="arch"
            PKG="pacman"
            ;;
        *)
            # Try ID_LIKE as fallback
            case "${ID_LIKE:-}" in
                *debian*|*ubuntu*) DISTRO="debian"; PKG="apt" ;;
                *fedora*|*rhel*)   DISTRO="fedora"; PKG="dnf" ;;
                *arch*)            DISTRO="arch";   PKG="pacman" ;;
            esac
            ;;
    esac
fi

if [ "$DISTRO" = "unknown" ]; then
    error "Could not detect Linux distribution. Supported: Ubuntu/Debian, Fedora/RHEL, Arch"
fi

info "Detected: $DISTRO (package manager: $PKG)"

# --- Helper: install packages ---------------------------------------------
install_packages() {
    case "$PKG" in
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y -qq "$@"
            ;;
        dnf)
            sudo dnf install -y -q "$@"
            ;;
        pacman)
            sudo pacman -Sy --noconfirm --needed "$@"
            ;;
    esac
}

# --- 1. Python 3.11+ ------------------------------------------------------
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
    case "$PKG" in
        apt)
            # Add deadsnakes PPA for newer Python on older Ubuntu
            if ! apt-cache show python3.12 &>/dev/null 2>&1; then
                sudo apt-get install -y -qq software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt-get update -qq
            fi
            install_packages python3.12 python3.12-venv python3.12-dev
            # Make python3.12 the default python3 if needed
            sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 2>/dev/null || true
            ;;
        dnf)
            install_packages python3.12 python3.12-devel python3.12-pip
            ;;
        pacman)
            install_packages python
            ;;
    esac
    success "Python installed"
else
    success "Python $PY_VERSION found (3.11+ required)"
fi

# Ensure pip and venv are available
case "$PKG" in
    apt)  install_packages python3-pip python3-venv 2>/dev/null || true ;;
    dnf)  install_packages python3-pip 2>/dev/null || true ;;
esac

# --- 2. Node.js 20+ -------------------------------------------------------
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
    case "$PKG" in
        apt)
            # NodeSource setup for Node.js 20
            if ! command -v node &>/dev/null || (( $(node --version | sed 's/v//' | cut -d. -f1) < 20 )); then
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                sudo apt-get install -y -qq nodejs
            fi
            ;;
        dnf)
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo -E bash -
            sudo dnf install -y -q nodejs
            ;;
        pacman)
            install_packages nodejs npm
            ;;
    esac
    success "Node.js installed"
else
    success "Node.js $(node --version) found (v20+ required)"
fi

# --- 3. PostgreSQL ---------------------------------------------------------
if ! command -v psql &>/dev/null; then
    info "Installing PostgreSQL..."
    case "$PKG" in
        apt)    install_packages postgresql postgresql-contrib libpq-dev ;;
        dnf)    install_packages postgresql-server postgresql-devel
                sudo postgresql-setup --initdb 2>/dev/null || true
                ;;
        pacman) install_packages postgresql
                sudo -u postgres initdb --locale en_US.UTF-8 -D /var/lib/postgres/data 2>/dev/null || true
                ;;
    esac
    success "PostgreSQL installed"
else
    success "PostgreSQL already installed"
fi

# Start PostgreSQL
if ! pg_isready -q 2>/dev/null; then
    info "Starting PostgreSQL..."
    sudo systemctl enable postgresql 2>/dev/null || true
    sudo systemctl start postgresql
    sleep 2
    if pg_isready -q 2>/dev/null; then
        success "PostgreSQL started"
    else
        warn "PostgreSQL may not have started — run.py --auto-setup will retry"
    fi
else
    success "PostgreSQL is running"
fi

# Create database and user
info "Setting up database..."
sudo -u postgres psql -c "CREATE USER dyslex WITH PASSWORD 'dyslex';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE dyslex OWNER dyslex;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dyslex TO dyslex;" 2>/dev/null || true
success "Database 'dyslex' ready"

# --- 4. Redis --------------------------------------------------------------
if ! command -v redis-server &>/dev/null; then
    info "Installing Redis..."
    case "$PKG" in
        apt)    install_packages redis-server ;;
        dnf)    install_packages redis ;;
        pacman) install_packages redis ;;
    esac
    success "Redis installed"
else
    success "Redis already installed"
fi

if ! redis-cli ping &>/dev/null 2>&1; then
    info "Starting Redis..."
    sudo systemctl enable redis 2>/dev/null || sudo systemctl enable redis-server 2>/dev/null || true
    sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null || true
    sleep 2
    success "Redis started"
else
    success "Redis is running"
fi

# --- 5. Build tools (needed for some Python packages) ----------------------
info "Ensuring build tools are installed..."
case "$PKG" in
    apt)    install_packages build-essential ;;
    dnf)    install_packages gcc gcc-c++ make ;;
    pacman) install_packages base-devel ;;
esac
success "Build tools ready"

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
echo ""
echo -e "    ${BOLD}python3 run.py --auto-setup${NC}"
echo ""
echo -e "  Or to start now automatically:"
echo ""
echo -e "    ${BOLD}python3 run.py --auto-setup --no-https${NC}"
echo ""
echo -e "  For HTTPS (recommended), first generate dev certificates:"
echo ""
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
