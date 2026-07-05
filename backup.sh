#!/bin/sh
set -e

COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="backups/$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"/uploads

echo "Dumping database..."
docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U postgres store_catalog | gzip > "$BACKUP_DIR"/store_catalog.sql.gz

echo "Copying uploads..."
docker compose -f "$COMPOSE_FILE" cp backend:/app/uploads/. "$BACKUP_DIR"/uploads/

echo ""
echo "Backup complete: $BACKUP_DIR"
echo "  DB:  $(du -h "$BACKUP_DIR/store_catalog.sql.gz" | cut -f1)"
echo "  Images: $(find "$BACKUP_DIR/uploads" -type f | wc -l) files ($(du -sh "$BACKUP_DIR/uploads" | cut -f1))"
