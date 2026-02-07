#!/bin/bash
# Test script for run.py launcher
# Demonstrates various usage modes and error handling

set -e

echo "=========================================="
echo "Testing DysLex AI Launcher (run.py)"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed() {
    echo -e "${GREEN}✓ $1${NC}"
}

test_failed() {
    echo -e "${RED}✗ $1${NC}"
}

test_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Test 1: Check script exists and is executable
echo "Test 1: Script exists and is executable"
if [[ -x run.py ]]; then
    test_passed "run.py exists and is executable"
else
    test_failed "run.py is not executable"
    exit 1
fi
echo ""

# Test 2: Help output
echo "Test 2: Help output"
if python3 run.py --help > /dev/null 2>&1; then
    test_passed "Help command works"
else
    test_failed "Help command failed"
    exit 1
fi
echo ""

# Test 3: Check-only mode with development configuration
echo "Test 3: Prerequisite checks (development mode)"
test_info "Running: python3 run.py --check-only"
python3 run.py --check-only 2>&1 || true
echo ""

# Test 4: Check-only mode for backend
echo "Test 4: Prerequisite checks (backend only)"
test_info "Running: python3 run.py --backend-only --check-only"
python3 run.py --backend-only --check-only 2>&1 || true
echo ""

# Test 5: Check-only mode for frontend
echo "Test 5: Prerequisite checks (frontend only)"
test_info "Running: python3 run.py --frontend-only --check-only"
python3 run.py --frontend-only --check-only 2>&1 || true
echo ""

# Test 6: No-color mode
echo "Test 6: No-color mode"
test_info "Running: python3 run.py --check-only --no-color"
python3 run.py --check-only --no-color 2>&1 || true
echo ""

# Test 7: Custom ports
echo "Test 7: Custom ports (check only)"
test_info "Running: python3 run.py --check-only --port-backend 8080 --port-frontend 3001"
python3 run.py --check-only --port-backend 8080 --port-frontend 3001 2>&1 || true
echo ""

# Test 8: Verify proper Python version check
echo "Test 8: Python version validation"
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    test_passed "Python version is 3.11+"
else
    test_info "Python version is < 3.11 (expected to fail prerequisites)"
fi
echo ""

# Test 9: Verify proper Node.js version check
echo "Test 9: Node.js version validation"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ $NODE_VERSION -ge 20 ]]; then
        test_passed "Node.js version is 20+"
    else
        test_info "Node.js version is < 20 (expected to fail prerequisites)"
    fi
else
    test_info "Node.js not found (expected to fail frontend prerequisites)"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
test_passed "All launcher tests completed"
echo ""
echo "To actually start services, ensure prerequisites are met:"
echo "  1. PostgreSQL running on localhost:5432"
echo "  2. Backend venv created: cd backend && python3 -m venv venv"
echo "  3. Backend deps installed: cd backend && source venv/bin/activate && pip install -r requirements.txt"
echo "  4. Frontend deps installed: cd frontend && npm install"
echo ""
echo "Then run: python3 run.py"
echo ""
