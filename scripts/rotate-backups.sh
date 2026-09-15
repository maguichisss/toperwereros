#!/bin/sh
# Prune old backups/ directories, keeping the newest N (default 5).
set -e

KEEP="${1:-5}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"

[ -d "$BACKUP_ROOT" ] || { echo "no $BACKUP_ROOT directory; nothing to prune"; exit 0; }

# shellcheck disable=SC2012
count=$(ls -1d "$BACKUP_ROOT"/*/ 2>/dev/null | wc -l)
if [ "$count" -le "$KEEP" ]; then
    echo "Keeping $count backup(s) (limit $KEEP). Nothing to prune."
    exit 0
fi

# shellcheck disable=SC2012
ls -1dt "$BACKUP_ROOT"/*/ | tail -n +$((KEEP + 1)) | while read -r dir; do
    echo "Pruning: $dir"
    rm -rf "$dir"
done

# shellcheck disable=SC2012
echo "Remaining backups: $(ls -1d "$BACKUP_ROOT"/*/ 2>/dev/null | wc -l)"