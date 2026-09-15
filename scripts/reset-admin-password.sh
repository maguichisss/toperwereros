#!/bin/sh
# Reset the password of the seeded `admin` user (occasion: forgot credentials).
# Passwords are written to the DB with bcrypt via the backend process image, so
# the update stays consistent with the app's own hashing.
set -e

[ "$#" -eq 1 ] || { echo "usage: $0 <new-password>" >&2; exit 1; }

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PASSWORD="$1"

docker compose -f "$COMPOSE_FILE" exec -T backend python - "$PASSWORD" <<'PY'
import sys
from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        sys.exit("admin user not found - run scripts/seed.sh first")
    user.hashed_password = hash_password(sys.argv[1])
    db.commit()
    print("admin password updated")
finally:
    db.close()
PY