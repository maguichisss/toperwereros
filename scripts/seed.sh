#!/bin/sh
# Re-seed default data (categories, colors, roles, default admin).
# Idempotent: safe to run repeatedly. Needed after a raw DB wipe outside the
# normal compose flow (the backend entrypoint also seeds on every boot).
set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

docker compose -f "$COMPOSE_FILE" exec -T backend python seed.py