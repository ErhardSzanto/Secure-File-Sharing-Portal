#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  echo "Missing backend virtualenv. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

source .venv/bin/activate

python - <<'PY'
import importlib.util as u
if not u.find_spec("pytest"):
    raise SystemExit("Missing dependency: pytest. Run ./scripts/bootstrap.sh")
PY

exec python -m pytest
