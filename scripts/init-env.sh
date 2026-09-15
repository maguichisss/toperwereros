#!/bin/sh
# Fresh-environment setup: create backend/.env from .env.example if absent,
# injecting a freshly generated JWT_SECRET. Never overwrites an existing .env.
set -e

ENV_FILE="backend/.env"
ENV_EXAMPLE="backend/.env.example"

[ -f "$ENV_FILE" ] && { echo "already exists: $ENV_FILE (leaving untouched)"; exit 0; }
[ -f "$ENV_EXAMPLE" ] || { echo "error: $ENV_EXAMPLE not found" >&2; exit 1; }

if ! grep -q '^JWT_SECRET=' "$ENV_EXAMPLE"; then
    echo "error: no JWT_SECRET= line in $ENV_EXAMPLE to substitute" >&2
    exit 1
fi

secret=$("$SHELL" -c 'openssl rand -hex 32 2>/dev/null || :')
if [ -z "$secret" ]; then
    echo "error: openssl not available to generate a JWT_SECRET" >&2
    exit 1
fi

sed "s/^JWT_SECRET=.*/JWT_SECRET=$secret/" "$ENV_EXAMPLE" > "$ENV_FILE"
echo "created $ENV_FILE with a fresh JWT_SECRET"