#!/usr/bin/env bash
# ============================================================================
# DysLex AI — Bootstrap Script
# ============================================================================
# Minimal script that ensures Python 3.11+ is installed, then delegates
# everything else to run.py --auto-setup.
#
# Use this when Python might not be installed yet:
#   curl -fsSL <raw-url>/scripts/bootstrap.sh | bash
#   — or —
#   chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[  ok]${NC}  $*"; }
error()   { echo -e "${RED}[fail]${NC}  $*"; exit 1; }

echo ""
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo -e "${BOLD}${CYAN}  DysLex AI — Bootstrap${NC}"
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo ""

# --- Detect project root --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)" || PROJECT_ROOT="$(pwd)"
cd "$PROJECT_ROOT"

# --- Check for run.py -----------------------------------------------------
if [[ ! -f "run.py" ]]; then
    error "run.py not found in $PROJECT_ROOT. Please run this script from the project root or scripts/ directory."
fi

# --- Check Python 3.11+ ---------------------------------------------------
needs_python() {
    if ! command -v python3 &>/dev/null; then
        return 0  # needs install
    fi
    local py_major py_minor
    py_major=$(python3 -c 'import sys; print(sys.version_info.major)' 2>/dev/null) || return 0
    py_minor=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || return 0
    if (( py_major < 3 || (py_major == 3 && py_minor < 11) )); then
        return 0  # needs upgrade
    fi
    return 1  # good
}

if needs_python; then
    info "Python 3.11+ not found. Installing..."

    OS="$(uname -s)"
    case "$OS" in
        Darwin)
            # macOS — use Homebrew
            if ! command -v brew &>/dev/null; then
                info "Installing Homebrew first..."
                NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                # Add brew to PATH for Apple Silicon
                if [[ -f /opt/homebrew/bin/brew ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                fi
            fi
            brew install python@3.12
            success "Python 3.12 installed via Homebrew"
            ;;
        Linux)
            # Detect package manager
            if [[ -f /etc/os-release ]]; then
                . /etc/os-release
                case "${ID:-}${ID_LIKE:-}" in
                    *debian*|*ubuntu*)
                        info "Installing Python 3.12 via apt..."
                        sudo apt-get update -qq
                        if ! apt-cache show python3.12 &>/dev/null 2>&1; then
                            sudo apt-get install -y -qq software-properties-common
                            sudo add-apt-repository -y ppa:deadsnakes/ppa
                            sudo apt-get update -qq
                        fi
                        sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
                        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 2>/dev/null || true
                        ;;
                    *fedora*|*rhel*)
                        info "Installing Python 3.12 via dnf..."
                        sudo dnf install -y -q python3.12 python3.12-devel python3.12-pip
                        ;;
                    *arch*)
                        info "Installing Python via pacman..."
                        sudo pacman -Sy --noconfirm --needed python
                        ;;
                    *)
                        error "Unsupported Linux distribution: ${ID:-unknown}. Please install Python 3.11+ manually."
                        ;;
                esac
            else
                error "Cannot detect Linux distribution. Please install Python 3.11+ manually."
            fi
            success "Python installed"
            ;;
        *)
            error "Unsupported OS: $OS. Please install Python 3.11+ manually, then run: python3 run.py --auto-setup"
            ;;
    esac

    # Verify
    if needs_python; then
        error "Python 3.11+ installation failed. Please install manually: https://python.org/downloads"
    fi
else
    success "Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') found"
fi

# --- Hand off to run.py ---------------------------------------------------
info "Handing off to run.py --auto-setup..."
echo ""
exec python3 run.py --auto-setup "$@"
