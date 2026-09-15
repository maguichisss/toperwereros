#!/bin/sh
# Generate a preview printable catalog: login with admin/employee credentials,
# fetch a themed PDF from the API, and save it as ./catalogo-preview.pdf.
#
# Credentials come from ADMIN_USER / ADMIN_PASSWORD (defaults: admin + the
# seeded DEFAULT_ADMIN_PASSWORD from backend/.env).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://localhost:3001}"
THEME="${1:-classic}"
OUT="${OUT:-catalogo-preview.pdf}"

ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(grep '^DEFAULT_ADMIN_PASSWORD=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2)}"

[ -n "$ADMIN_PASSWORD" ] || {
    echo "error: set ADMIN_PASSWORD (or DEFAULT_ADMIN_PASSWORD in backend/.env)" >&2
    exit 1
}

token=$(curl -fsS "$BACKEND_URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASSWORD\"}" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -fsS "$BACKEND_URL/api/catalog/pdf?theme=$THEME" \
    -H "Authorization: Bearer $token" -o "$OUT"

echo "Catalog preview written to $OUT (theme: $THEME)"