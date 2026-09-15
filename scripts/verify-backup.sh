#!/bin/sh
# Verify a backup directory: SQL dump is a valid gzip, non-empty, and the
# uploads copy is present.
set -e

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ]; then
    # shellcheck disable=SC2012
    BACKUP_DIR="backups/$(ls -1t backups/ | head -1)"
fi

[ -d "$BACKUP_DIR" ] || { echo "error: $BACKUP_DIR not found" >&2; exit 1; }

DUMP="$BACKUP_DIR/store_catalog.sql.gz"

echo "== $BACKUP_DIR =="
if [ ! -f "$DUMP" ]; then
    echo "  FAIL: $DUMP missing" >&2
    exit 1
fi
gzip -t "$DUMP" && echo "  OK: gzip integrity"
size=$(stat -c %s "$DUMP" 2>/dev/null || stat -f %z "$DUMP")
[ "$size" -gt 0 ] && echo "  OK: dump size $size bytes" || { echo "  FAIL: dump is empty" >&2; exit 1; }

if [ -d "$BACKUP_DIR/uploads" ]; then
    files=$(find "$BACKUP_DIR/uploads" -type f | wc -l)
    echo "  OK: uploads present ($files file(s))"
else
    echo "  WARN: no uploads/ directory in this backup"
fi

echo "Verify complete."