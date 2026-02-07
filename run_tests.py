#!/usr/bin/env python3
"""Run all tests (backend + frontend) for DysLex AI.

Usage: python3 run_tests.py [pytest args...]
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / "backend" / "venv" / "bin" / "python"
TESTS_DIR = ROOT / "backend" / "tests"
FRONTEND_DIR = ROOT / "frontend"


def run_backend_tests(extra_args: list[str]) -> int:
    if not VENV_PYTHON.exists():
        print(f"Warning: backend venv not found at {VENV_PYTHON}")
        print("Run 'python3 run.py --auto-setup' first to create it.")
        print("Skipping backend tests.\n")
        return 0

    print("Running backend tests...\n")
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", str(TESTS_DIR), "-v", *extra_args],
    )
    return result.returncode


def run_frontend_tests() -> int:
    npx = "npx"
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Warning: frontend node_modules not found.")
        print("Run 'cd frontend && npm install' first.")
        print("Skipping frontend tests.\n")
        return 0

    print("\nRunning frontend tests...\n")
    result = subprocess.run(
        [npx, "vitest", "run", "--reporter=verbose"],
        cwd=str(FRONTEND_DIR),
    )
    return result.returncode


def main() -> int:
    extra_args = sys.argv[1:]

    backend_rc = run_backend_tests(extra_args)
    frontend_rc = run_frontend_tests()

    if backend_rc != 0 or frontend_rc != 0:
        print("\nSome tests failed.")
        return 1

    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
