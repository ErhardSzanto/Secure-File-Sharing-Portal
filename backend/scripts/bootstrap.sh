#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -m pip install -r requirements.txt; then
  echo "Dependency install failed. Check internet/proxy access, then rerun ./scripts/bootstrap.sh." >&2
  exit 1
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

mkdir -p uploads

echo "Backend bootstrap complete."
echo "Interpreter: $(which python)"
echo "Run server: ./scripts/dev.sh"
echo "Run tests:  ./scripts/test.sh"
