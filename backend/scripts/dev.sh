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
missing = [m for m in ("uvicorn", "fastapi", "sqlalchemy") if not u.find_spec(m)]
if missing:
    raise SystemExit("Missing dependencies: " + ", ".join(missing) + ". Run ./scripts/bootstrap.sh")
PY

exec python -m uvicorn app.main:app --reload --host localhost --port 8000
