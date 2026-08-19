#!/bin/sh
set -e

: ${BACKEND_URL:=http://localhost:8080}
BACKEND_HOST=$(echo "$BACKEND_URL" | sed 's|https\?://||;s|[:/].*||')
export BACKEND_HOST
envsubst '$BACKEND_URL $BACKEND_HOST' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
