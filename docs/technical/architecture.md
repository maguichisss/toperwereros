# Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Browser (SPA)                          │
│  React 18 + Vite — tabs: Productos · Apartados ·              │
│  Administración · Perfil                                       │
└───────────────┬──────────────────────────────────────────────┘
                │  /api/*  and  /uploads/*   (same origin / proxied)
┌───────────────▼──────────────────────────────────────────────┐
│  Server (nginx in prod, Vite proxy in dev)                   │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│  FastAPI  (uvicorn/gunicorn single process, sync routes)      │
│                                                              │
│  Routers under /api:                                          │
│    auth · products · categories · colors · upload · catalog  │
│    sales · customers · layaways                               │
│  + /docs (custom HTML) · /redoc · /api/health                 │
└──────┬───────────────┬────────────────────────────┬──────────┘
       │               │                            │
┌──────▼───────┐ ┌─────▼──────┐           ┌─────────▼──────────┐
│ SQLAlchemy   │ │ Uploads    │           │ fpdf2 + Pillow     │
│ + PostgreSQL │ │ (local disk│           │ PDF/HTML catalog   │
│ (or CloudSQL)│ │  or GCS)   │           │ generator          │
└──────────────┘ └────────────┘           └────────────────────┘
```

## Backend

FastAPI application defined in [`backend/app/main.py`](../../backend/app/main.py). Design points:

- **Single file routers** in [`backend/app/routers/`](../../backend/app/routers), mounted under `/api/`
  prefixes (e.g. `app.include_router(products.router, prefix="/api/products")`).
- **Sync endpoints** run in a threadpool; the ORM session is provided by a
  `get_db` dependency that always closes the session.
- **Custom docs** replace the default OpenAPI UI:
  - `/docs` serves [`backend/docs.html`](../../backend/docs.html) (a hand-maintained document, source of
    truth [`docs/api-reference.md`](../api-reference.md)).
  - `/swagger` exposes the generated OpenAPI schema (FastAPI default).
  - `/redoc` serves a pinned ReDoc (v2.1.5) over the OpenAPI schema.
- **Health check** at `/api/health` runs `SELECT 1` and returns 503 when the DB
  is unreachable (used by Cloud Run probes).
- **Uploads** static mount `/uploads` is added only when `GCS_BUCKET` is empty
  (local disk mode); with GCS the files are served from cloud storage instead.
- **Rate limiting** (slowapi) — login is limited to 5 requests/minute per
  client key; a global `RateLimitExceeded` handler returns the JSON error body.

### Layer layout ([`backend/app/`](../../backend/app))

| Module | Responsibility |
| --- | --- |
| [`main.py`](../../backend/app/main.py) | App factory, middleware, routers, `/docs`, `/api/health` |
| [`config.py`](../../backend/app/config.py) | Env config, upload paths, `escape_like`, GCS flag |
| [`database.py`](../../backend/app/database.py) | Engine, `SessionLocal`, declarative `Base`, `get_db` |
| [`models.py`](../../backend/app/models.py) | SQLAlchemy ORM — 11 tables (see [database.md](database.md)) |
| [`schemas.py`](../../backend/app/schemas.py) | Pydantic request/response models |
| [`auth.py`](../../backend/app/auth.py) | bcrypt, JWT, refresh-token rotation, `ROLE_PERMISSIONS`, guards |
| [`gcs.py`](../../backend/app/gcs.py) | Google Cloud Storage client (only when `GCS_BUCKET` set) |
| [`patterns.py`](../../backend/app/patterns.py) | Background pattern generator for themed PDF catalogs |
| [`logging_config.py`](../../backend/app/logging_config.py) | Logging setup (`LOG_LEVEL`) |
| [`routers/`](../../backend/app/routers) | API routers (see above) |
| `fonts/` | Bundled DejaVu TrueType fonts used by the PDF renderer |

### Conventions

- Error messages returned to users are **Spanish** (e.g. `"Stock insuficiente …"`),
  while code, logs, and docs are English.
- Mutations are transactional: sales and layaway completion wrap writes in
  `db.begin_nested()` savepoints so stock is never partially debited.
- Pagination conventions: products default `per_page=20` (max 200), sales and
  layaways `per_page=20` (max 100) — both 1-indexed `page` (>= 1).

## Frontend

React SPA in [`frontend/`](../../frontend), built with Vite and served by nginx in production.

- **Navigation** ([`frontend/src/App.jsx`](../../frontend/src/App.jsx)): four tabs —
  `Productos`, `Apartados`, `Administración`, `Perfil`.
- **Administration subtabs** ([`frontend/src/components/ManagementPage.jsx`](../../frontend/src/components/ManagementPage.jsx)):
  `Clientes`, `Ventas`, `Colores`, `Categorías`, `Usuarios`
  (Colores/Categorías/Usuarios are admin-only).
- **Cart** (`CartPanel`) is the POS drawer: adding stock doesn't lock anything
  until a sale or layaway is confirmed against the backend.
- **API client** ([`frontend/src/api/client.js`](../../frontend/src/api/client.js)): every request attaches
  `Authorization: Bearer <store_token>`; on a 401 it refreshes once via
  `/api/auth/refresh` using a shared promise (so concurrent requests collapse
  into one refresh), then retries.
- **Token storage** ([`frontend/src/context/AuthContext.jsx`](../../frontend/src/context/AuthContext.jsx)): access + refresh
  JWTs live in `localStorage` under `store_token` / `store_refresh_token`;
  silent refresh happens on app boot when the token is expired.
- **Permissions** are mirrored client-side in `can(permission)` so the UI hides
  actions the user cannot perform; the backend remains the authority.
- **Styles** are plain CSS in `frontend/src/styles/*.css`, imported from
  [`frontend/src/main.jsx`](../../frontend/src/main.jsx) (variables, base, layout, components).

### Dev-server proxy ([`frontend/vite.config.js`](../../frontend/vite.config.js))

`/api` and `/uploads` proxy to `VITE_PROXY_TARGET` (default
`http://localhost:3001`); polling file-watching is enabled for containerized
dev; optional HTTPS via `VITE_HTTPS_CERT`/`VITE_HTTPS_KEY`.

## Data flows in one line

UI tab → [`client.js`](../../frontend/src/api/client.js) (auth headers + single-flight refresh) → FastAPI router →
permission guard (`require_permission`) → Pydantic schema → ORM transaction →
PostgreSQL. Catalog output additionally streams through the PDF/HTML renderer
([`catalog.py`](../../backend/app/routers/catalog.py)) reading images from local disk or GCS.

## Deployment topologies

Three supported shapes (details in [deployment.md](deployment.md)):

1. **Local dev** — `docker compose up`: postgres, backend on :3001, Vite on :5173.
2. **Raspberry Pi** — [`docker-compose.pi.yml`](../../docker-compose.pi.yml): db, gunicorn backend :8080,
   nginx terminator on 80/443 with mkcert TLS.
3. **Cloud Run + Cloud SQL** — [`docker-compose.prod.yml`](../../docker-compose.prod.yml) + `scripts/deploy*.sh`, with
   an amd64 Cloud SQL-proxy sidecar on outbound 5432.