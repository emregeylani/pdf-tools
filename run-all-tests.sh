#!/usr/bin/env bash
set -euo pipefail

VENV=".venv-pdf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── venv ──────────────────────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

# ── dependencies ──────────────────────────────────────────────────────────────
pip install -q -r requirements.txt
pip install -q pytest pytest-mock

# ── run ───────────────────────────────────────────────────────────────────────
exec python -m pytest tests/ -v "$@"
