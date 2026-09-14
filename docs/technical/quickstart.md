# Quick start (local, no Docker)

Requires Python 3.11+ and Node 20+.

## Backend

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# PostgreSQL must be reachable at DATABASE_URL (see backend/.env.example)
# e.g. export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/store_catalog
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

python -m seed                 # categories, colors, roles, admin user
uvicorn app.main:app --reload --port 3001
```

- API: http://localhost:3001 — Solar swagger at `/swagger`, custom docs at
  `/docs`, health at `/api/health`.
- Default admin login: `admin` / `DEFAULT_ADMIN_PASSWORD` (`admin123` unless
  overridden — change it).

## Frontend

```sh
cd frontend
npm ci
VITE_PROXY_TARGET=http://localhost:3001 npm run dev
```

The dev server (http://localhost:5173) proxies `/api` and `/uploads` to the
backend. Optional HTTPS is enabled by setting `VITE_HTTPS_CERT` and
`VITE_HTTPS_KEY`.

## Tests

```sh
cd backend
pytest                                  # full suite (SQLite-backed per module)
pytest -k docs                          # only the docs-drift guards
```

See [testing.md](testing.md) for details.

## Troubleshooting

- **`RuntimeError: JWT_SECRET … required`** — the variable is read at import
  time; set it before starting uvicorn.
- **CORS errors from the SPA** — `CORS_ORIGINS` must include the frontend origin
  (or `*` in dev).
- **Uploads 404** — the `/uploads` static mount is only added when `GCS_BUCKET`
  is empty.