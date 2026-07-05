#!/bin/bash
set -e

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ]; then
    echo "Available backups:"
    ls -1 backups/
    echo ""
    read -p "Enter backup directory name (e.g. 2026-07-04_142250): " dir
    BACKUP_DIR="backups/$dir"
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory '$BACKUP_DIR' not found"
    exit 1
fi
if [ ! -f "$BACKUP_DIR/store_catalog.sql.gz" ]; then
    echo "Error: '$BACKUP_DIR/store_catalog.sql.gz' not found"
    exit 1
fi

echo "Restoring from $BACKUP_DIR"

docker compose -f docker-compose.yml stop backend

echo "Restoring database..."
echo "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'store_catalog' AND pid <> pg_backend_pid(); DROP DATABASE IF EXISTS store_catalog; CREATE DATABASE store_catalog;" | docker compose -f docker-compose.yml exec -T db psql -U postgres
gunzip -c "$BACKUP_DIR/store_catalog.sql.gz" | docker compose -f docker-compose.yml exec -T db psql -U postgres store_catalog

echo "Starting backend for upload restore..."
docker compose -f docker-compose.yml start backend

echo "Restoring uploads..."
docker compose -f docker-compose.yml exec -T backend rm -rf /app/uploads/*
docker compose -f docker-compose.yml cp "$BACKUP_DIR/uploads/." backend:/app/uploads/

echo "Restore complete: $BACKUP_DIR"
