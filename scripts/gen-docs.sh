#!/bin/sh
# Regenerate backend/docs.html from docs/api-reference.md and run the two
# documentation drift tests. Run after editing the API reference.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/backend/.venv/bin/python"

if [ ! -x "$VENV" ]; then
    echo "error: backend/.venv not found. Create it with:" >&2
    echo "  python -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements-dev.txt" >&2
    exit 1
fi

cd "$ROOT/backend"
"$VENV" scripts/gen_api_docs.py
"$VENV" -m pytest tests/test_docs_generated.py tests/test_docs_permissions.py -q