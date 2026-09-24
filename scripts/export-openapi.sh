#!/bin/sh
# Dump the backend OpenAPI schema snapshot to ./openapi.json (dev utility for
# contract diffing / tooling). Uses the backend virtualenv.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/backend/.venv/bin/python"

if [ ! -x "$VENV" ]; then
    echo "error: backend/.venv not found. Create it with:" >&2
    echo "  python -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements-dev.txt" >&2
    exit 1
fi

cd "$ROOT/backend"
JWT_SECRET="${JWT_SECRET:-dev-snapshot}" "$VENV" - <<'PY'
import json
from app.main import app
out = app.openapi()
print(json.dumps(out, indent=2, ensure_ascii=False))
PY