#!/bin/sh
set -e

# --- Start Cloud SQL Auth Proxy if connection string is provided ---
if [ -n "$CLOUD_SQL_CONNECTION_STRING" ]; then
    echo "Starting Cloud SQL Auth Proxy for $CLOUD_SQL_CONNECTION_STRING ..."
    cloud-sql-proxy \
        --port=5432 \
        --structured-logs \
        "$CLOUD_SQL_CONNECTION_STRING" &
    PROXY_PID=$!

    # Wait for proxy readiness (TCP check via Python, no netcat needed)
    READY=0
    for i in $(seq 1 30); do
        if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',5432),2); s.close()" 2>/dev/null; then
            echo "Cloud SQL Auth Proxy is ready."
            READY=1
            break
        fi
        if ! kill -0 "$PROXY_PID" 2>/dev/null; then
            echo "ERROR: Cloud SQL Auth Proxy exited unexpectedly."
            exit 1
        fi
        echo "Waiting for Cloud SQL Auth Proxy... ($i/30)"
        sleep 1
    done
    if [ "$READY" -eq 0 ]; then
        echo "ERROR: Cloud SQL Auth Proxy did not become ready in 30 seconds."
        exit 1
    fi
fi

echo "Ensuring tables exist..."
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
echo "Running migrations..."
alembic upgrade head

echo "Seeding data..."
python -m seed

echo "Starting application server..."

# Graceful shutdown: forward SIGTERM to proxy before exiting
_term() {
    echo "Received SIGTERM, shutting down..."
    if [ -n "$PROXY_PID" ]; then
        kill "$PROXY_PID" 2>/dev/null
        wait "$PROXY_PID"
    fi
    exit 0
}
trap _term TERM INT

# Start app server in foreground (proxy runs in background)
"$@" &
APP_PID=$!
wait "$APP_PID"
