# Deployment

The project ships three deployment topologies plus one-time infrastructure
tooling. All backend artifacts live in [`backend/`](../../backend) (Dockerfile + entrypoint);
frontend artifacts in [`frontend/`](../../frontend).

## Environment variables

See [`backend/.env.example`](../../backend/.env.example) for the canonical list. All are read via `os.getenv`
at import time (`backend/app/{config,auth,database}.py`).

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `JWT_SECRET` | **yes** | — | HS256 signing key (random 64+ chars in production) |
| `JWT_EXPIRE_MINUTES` | no | `1440` | Access-token lifetime in minutes |
| `DATABASE_URL` | no* | `postgresql://postgres:postgres@localhost:5432/store_catalog` | SQLAlchemy connection string |
| `CORS_ORIGINS` | no | `*` | Comma-separated allowed origins |
| `LOG_LEVEL` | no | `INFO` | Logging verbosity |
| `DEFAULT_ADMIN_PASSWORD` | no | `admin123` | Password for the seeded admin account |
| `GCS_BUCKET` | no | *(empty)* | Set to route uploads to Google Cloud Storage |
| `GCP_PROJECT` | no | — | GCP project id (GCS / Cloud SQL only) |
| `CLOUD_SQL_CONNECTION_STRING` | no | — | Starts the Cloud SQL Auth Proxy inside the container |

\* PostgreSQL is expected in every topology; the default only applies locally.

## 1. Local development ([`docker-compose.yml`](../../docker-compose.yml))

| Service | Image / build | Port | Purpose |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` + `pgdata` volume + healthcheck | 5432 | PostgreSQL |
| `backend` | [`backend/Dockerfile`](../../backend/Dockerfile) → `backend-dev` | 3001 | FastAPI (uvicorn `--reload`, bind-mounted source) |
| `frontend` | [`frontend/Dockerfile`](../../frontend/Dockerfile) → `frontend-dev` | 5173 | Vite dev server proxying `/api` → `http://backend:3001` |

The backend mounts `backend/.env`, and the compose file overrides
`DATABASE_URL` to reach the `db` service. The frontend dev target reads
`VITE_PROXY_TARGET`, `VITE_HTTPS_CERT` and `VITE_HTTPS_KEY`.

```sh
docker compose up --build
# backend  → http://localhost:3001  (swagger /swagger)
# frontend → http://localhost:5173  (Vite)
```

Non-Docker instructions live in [quickstart.md](quickstart.md).

## 2. Raspberry Pi QA ([`docker-compose.pi.yml`](../../docker-compose.pi.yml))

A standalone QA environment that does **not** depend on GCP. Prereqs: a 64-bit
Raspberry Pi (arm64), Docker + compose v2, mkcert TLS certs.

| Service | Target | Port | Notes |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | — | `POSTGRES_PASSWORD` from shell env (default `postgres`) |
| `backend` | `backend-pi` | 8080 | gunicorn, 2 workers, `.env.pi` |
| `frontend` | `frontend-pi` | 80/443 | nginx, static TLS, `nginx.pi.conf` |

Backend command: `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker
--bind 0.0.0.0:${PORT:-8080} --timeout 300`.

The full step-by-step runbook (Docker install, mkcert certs, `.env.pi`,
build/up, logs/bring-down) is [deployment.pi.md](deployment.pi.md).

Key nginx details on the Pi ([`frontend/nginx.pi.conf`](../../frontend/nginx.pi.conf)):

- HTTP :80 redirects to HTTPS :443 (mkcert `pi.pem` / `pi-key.pem`).
- `client_max_body_size 6m` (enough for product photos).
- `/api/` and `/uploads/` proxy to `http://backend:8080`; buffers 128k / 4×256k;
  proxy read/send timeout 300s.
- SPA fallback: `try_files $uri $uri/ /index.html`.

## 3. Google Cloud Run + Cloud SQL ([`docker-compose.prod.yml`](../../docker-compose.prod.yml))

| Service | Image | Notes |
| --- | --- | --- |
| `cloudsql-proxy` | `gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1` | `--port=5432`, SA creds read from `./secrets/service-account.json` |
| `backend` | `backend-prod` | `DATABASE_URL` points to `127.0.0.1:5432` via the proxy |
| `frontend` | `frontend-prod` | nginx template with `BACKEND_URL` envsubst |

The `backend-prod` image embeds the **Cloud SQL Auth Proxy** binary in the
container (amd64). `docker-entrypoint.sh` starts the proxy first when
`CLOUD_SQL_CONNECTION_STRING` is set, waits for a TCP connection on :5432, then
boots the app.

### Boot sequence ([`backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh))

1. If `CLOUD_SQL_CONNECTION_STRING` set → start proxy, poll (30×1 s) for
   readiness, fail fast if the proxy dies.
2. `Base.metadata.create_all(bind=engine)` — ensure tables exist.
3. If `alembic_version` exists → `alembic upgrade head`, else `alembic stamp head`.
4. `python -m seed` — idempotent categories, colors, roles, and default admin.
5. Start the app server and forward SIGTERM to the proxy on shutdown.

### One-time GCP setup ([`deploy/01-setup-infra.sh`](../../deploy/01-setup-infra.sh))

Requires `GCP_PROJECT`, `DB_PASSWORD`, `GCS_BUCKET`, `JWT_SECRET`,
`DEFAULT_ADMIN_PASSWORD` env vars. Creates:

- enabled APIs: run, sqladmin, storage, artifactregistry, secretmanager, iamcredentials;
- Artifact Registry repo `store-catalog`;
- Cloud SQL `POSTGRES_16` instance `store-catalog` (db-f1-micro, 10 GB
  auto-increase, backups at 03:00, `--no-assign-ip`);
- GCS bucket + `objectAdmin` grant to the backend SA;
- backend SA `store-catalog-backend` with `cloudsql.client`,
  `secretmanager.secretAccessor`, and bucket objectAdmin;
- Secret Manager secrets: `jwt-secret`, `admin-password`, `db-password`,
  `db-url` (all with SA policies).

### Build & push ([`deploy/02-build-push.sh`](../../deploy/02-build-push.sh))

Builds `backend-prod` and `frontend-prod` targets and pushes to Artifact
Registry (`$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/store-catalog/{backend,frontend}:$TAG`).
`TAG` defaults to the short git SHA (`IMAGE_TAG` overrides).

### Deploy ([`deploy/03-deploy.sh`](../../deploy/03-deploy.sh))

- Deploys `store-catalog-backend` to Cloud Run: SA, `--add-cloudsql-instances`,
  secrets bound (`JWT_SECRET`, `DEFAULT_ADMIN_PASSWORD`, `DATABASE_URL`), env
  (`CLOUD_SQL_CONNECTION_STRING`, `GCS_BUCKET`, `CORS_ORIGINS`), port 8080,
  512 MiB, 1 vCPU, 0–10 instances, `--no-allow-unauthenticated`.
- Deploys `store-catalog-frontend` with `BACKEND_URL=<backend url>`.
- Finally updates the backend `CORS_ORIGINS` to the frontend URL.
- `/api/health` is the readiness/liveness probe target.

## Production nginx ([`frontend/nginx.conf`](../../frontend/nginx.conf), [`frontend/docker-entrypoint.sh`](../../frontend/docker-entrypoint.sh))

The `frontend-prod` image renders an nginx template via `envsubst`
(`$BACKEND_URL`, `$BACKEND_HOST`). Key points:

- listen 8080; `resolver 169.254.169.254` (GCP metadata DNS) lets `proxy_pass`
  resolve the Cloud Run service host at runtime.
- `/api/` and `/uploads/` proxied to the backend with connect timeout 60s and
  read/send timeout 300s (long requests like PDF generation).
- Static SPA files served by `try_files`.

## Backups & restore

- **[`backup.sh`](../../backup.sh)** — `pg_dump --no-owner -U postgres store_catalog | gzip` into
  `backups/<timestamp>/store_catalog.sql.gz`, then copies `/app/uploads` from
  the backend container ([`backup.sh`](../../backup.sh) caveat: leaves a stale `backups/` copy of
  own work behind only if run from the repo root).
- **`restore.sh [backup-dir]`** — stops backend → terminates stale connections /
  drop/recreate `store_catalog` → `psql` restore → starts backend →
  clears uploads and copies them back from the backup dir.

Both default to [`docker-compose.yml`](../../docker-compose.yml) (`COMPOSE_FILE` overrides, e.g. Pi).

## CI

[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) drives the GCP pipeline (setup → build/push →
deploy). Docker pushes from CI already gated behind conditions on that
workflow; run sizes/args are defined inline there.

## Operational checklist (all envs)

- [ ] `JWT_SECRET` set, random, ≥ 64 chars, **not** `dev-secret-change-in-production`
- [ ] `DEFAULT_ADMIN_PASSWORD` overridden from the default
- [ ] Seeded data applied once (entrypoint handles it idempotently)
- [ ] Uploads persisted: Pi backend volume / Cloud Storage bucket
- [ ] TLS certs mounted on the Pi (or Cloud Run-managed certs)
- [ ] Tests green before deploy (see [testing.md](testing.md))