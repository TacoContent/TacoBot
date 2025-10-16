#!/usr/bin/env bash
set -euo pipefail

# macOS specific note: ensure you are using the desired Python (possibly via pyenv)

echo "[tacobot] Creating virtual environment (.venv)..."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
else
  echo "[tacobot] .venv already exists; skipping creation."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[tacobot] Upgrading pip"
python -m pip install --upgrade pip wheel setuptools

deV=${1:-}
if [[ "$deV" == "--dev" || "$deV" == "-d" ]]; then
  echo "[tacobot] Installing project with dev extras"
  pip install -e .[dev,docs]
else
  echo "[tacobot] Installing project (runtime deps only)"
  pip install -e .
fi

echo "[tacobot] Finished. Activate with: source .venv/bin/activate"
