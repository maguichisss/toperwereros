#!/bin/sh
# DEV-ONLY: drop and recreate the local `store_catalog` database, then restart
# the backend so the entrypoint rebuilds the schema, stamps the alembic head,
# and re-seeds default data.
#
# Guards: requires typing RESET, and refuses to run against any compose file
# other than the dev docker-compose.yml unless ALLOW_REMOTE=1 is set.
set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

if [ "$COMPOSE_FILE" != "docker-compose.yml" ] && [ "$ALLOW_REMOTE" != "1" ]; then
    echo "error: $COMPOSE_FILE is not the dev file. Set ALLOW_REMOTE=1 to override." >&2
    exit 1
fi

echo "WARNING: this destroys the '$COMPOSE_FILE' database and ALL data in it."
read -r -p "Type RESET to continue: " answer
[ "$answer" = "RESET" ] || { echo "aborted"; exit 1; }

docker compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='store_catalog' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS store_catalog;" \
    -c "CREATE DATABASE store_catalog;"

docker compose -f "$COMPOSE_FILE" restart backend
echo "Database reset. Backend entrypoint will recreate schema and seed data on boot."