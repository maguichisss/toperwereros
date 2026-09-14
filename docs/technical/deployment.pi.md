# PI QA Runbook — Store Catalog on a Raspberry Pi

This runbook deploys the **QA environment** of store-catalog on a standalone
Raspberry Pi using Docker Compose. The Pi runs its own local PostgreSQL, the
backend (gunicorn), and an nginx frontend with TLS via mkcert certs. It does
**not** depend on GCP (no Cloud SQL, no Cloud Storage, no Cloud Run).

> The GCP `store-catalog-qa` Cloud SQL instance has been deprecated. QA lives
> on the Pi now (see `docker-compose.pi.yml`).

---

## Prerequisites

- Raspberry Pi 4 or 5 running a **64-bit OS** (e.g. Raspberry Pi OS Lite 64-bit).
  arm64 is required — the Postgres/Python/nginx images do not target 32-bit ARM.
- Docker Engine + the `docker compose` (v2) plugin installed.
- The Pi reachable on your LAN by hostname (mDNS, e.g. `store-qa.local`) or by IP.

---

## 1. Install Docker on the Pi

```sh
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker
sudo systemctl enable --now docker
docker compose version   # verify compose v2 is available
```

## 2. Copy the repository to the Pi

```sh
git clone <repo-url> ~/store-catalog
cd ~/store-catalog
```

## 3. Generate TLS certificates (mkcert)

mkcert creates a local root CA plus a certificate for your Pi hostname/IPs.

```sh
sudo apt install mkcert
mkdir -p certs
cd certs
mkcert -install
mkcert -cert-file pi.pem -key-file pi-key.pem \
  store-qa.local <pi-ip> localhost 127.0.0.1 ::1
cd ..
```

This produces `certs/pi.pem` and `certs/pi-key.pem`, which are mounted into the
frontend container (`./certs:/etc/nginx/certs:ro`) and referenced by
`frontend/nginx.pi.conf`.

## 4. Create `backend/.env.pi`

Copy the sample and set real values (**never commit secrets** — `.env*` is
gitignored and dockerignored):

```sh
cp backend/.env.example backend/.env.pi
nano backend/.env.pi
```

Minimum values to set:

| Variable | Value |
|---|---|
| `JWT_SECRET` | long random string (64+ chars) |
| `DEFAULT_ADMIN_PASSWORD` | strong password for the seeded admin |
| `CORS_ORIGINS` | `https://store-qa.local,https://<pi-ip>` (comma-separated) |
| `DATABASE_URL` | **do not set** — injected by compose |

`GCS_BUCKET` must stay empty so images are stored on the Pi's local disk and
served by the backend under `/uploads`.

## 5. Build and start the stack

```sh
docker compose -f docker-compose.pi.yml up -d --build
```

First boot runs the DB healthcheck, then the backend entrypoint applies
migrations (`alembic upgrade head`) and seeds the admin user before gunicorn
starts.

## 6. Trust the root CA on clients

On every laptop/phone that will access the QA site, install the mkcert root CA
(`certs/rootCA.pem`) and mark it trusted:

- **macOS/Windows/Linux**: `mkcert -install` on the client (with the same mkcert).
  Alternatively import `rootCA.pem` into the OS/browser trust store.
- **Android**: import `rootCA.pem` via *Settings → Security → Install CA*.
- **iOS**: install and enable full trust in *Settings → General → About → Certificate Trust*.

## 7. Access the QA site

- `https://store-qa.local/`
- or `https://<pi-ip>/`

Port 80 redirects to HTTPS. Only ports `80`/`443` are published; the backend and
DB are only reachable over the internal compose network.

## 8. Verification checklist

```sh
docker compose -f docker-compose.pi.yml ps                # 3 containers Up/Healthy
curl -sk https://localhost/api/health                     # {"status":"ok","db":"connected"}
```

In the browser:
1. Log in with the admin user created by the seed.
2. Add a product with an image > 1 MB (validates the nginx
   `client_max_body_size 6m` proxy path).
3. Create a sale and / or layaway (apartado) and confirm stock decrements.

## 9. Day-to-day operations

```sh
# Logs
docker compose -f docker-compose.pi.yml logs -f backend

# Restart the app only
docker compose -f docker-compose.pi.yml restart backend frontend

# Rebuild after a code change
docker compose -f docker-compose.pi.yml up -d --build

# Stop everything (data persists in volumes)
docker compose -f docker-compose.pi.yml down

# Full reset including databases/uploads
docker compose -f docker-compose.pi.yml down -v
```

## 10. Backup & restore

Backups snapshot the Postgres DB and the uploaded images. Each run creates
`backups/<timestamp>/` with `store_catalog.sql.gz` and `uploads/`.

```sh
# Desktop (dev DB) — uses docker-compose.yml
./backup.sh

# Pi (QA DB) — uses docker-compose.pi.yml
COMPOSE_FILE=docker-compose.pi.yml ./backup.sh
```

`COMPOSE_FILE` is Docker Compose's own convention, so exported it is honoured
by both the scripts and `docker compose` itself.

Copy a backup to the Pi:

```sh
scp -r backups/2026-09-08_194717 pi-user@<pi-ip>:~/store-catalog/backups/
```

Restore on the Pi (stops backend, drops/recreates `store_catalog`, restores the
dump + uploads):

```sh
COMPOSE_FILE=docker-compose.pi.yml ./restore.sh backups/2026-09-08_194717
```

Notes:

- Passwords/roles/users come from the backup (e.g. dev `admin`).
- `alembic_version` is restored at head, so the next backend boot runs a no-op
  `alembic upgrade head`.
- Verify afterwards: `curl -sk https://localhost/api/health` and check a product
  image.

## Notes

- **QA DB name**: `store_catalog` (inside container `db`).
- **Persistent data**: `pgdata` (Postgres) and `backend_uploads` (images) volumes.
- **Renewing certs**: re-run the mkcert command in step 3, then
  `docker compose -f docker-compose.pi.yml restart frontend`.
- To serve on the Pi's actual hostname, replace `store-qa.local` above and keep
  `CORS_ORIGINS` in sync.