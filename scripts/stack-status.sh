#!/bin/sh
# Quick stack health snapshot: compose service status + backend /api/health.
set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
BACKEND_URL="${BACKEND_URL:-http://localhost:3001}"

echo "== docker compose ps ($COMPOSE_FILE) =="
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "== backend health ($BACKEND_URL/api/health) =="
code=$(curl -s -o /tmp/stack-health-body.$$ -w '%{http_code}' "$BACKEND_URL/api/health" || true)
rm -f /tmp/stack-health-body.$$
if [ "$code" = "200" ]; then
    echo "OK (HTTP $code)"
else
    echo "UNHEALTHY (HTTP ${code:-no response})"
    exit 1
fi