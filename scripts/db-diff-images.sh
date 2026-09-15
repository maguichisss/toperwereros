#!/bin/sh
# Image-hygiene utility: report (or --delete) product images that are out of
# sync between the uploads volume and the products.image_url column.
# Wraps backend/db_diff_imgs.py running inside the backend container.
set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

docker compose -f "$COMPOSE_FILE" exec -T backend python db_diff_imgs.py "$@"