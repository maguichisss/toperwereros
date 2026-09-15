# Store Catalog

Store management system for **Toperwereros**: a product catalog with POS-style
sales, layaway plans (apartados), and printable PDF catalogs.

## Repo layout

| Path | What it is |
| --- | --- |
| [`backend/`](backend) | FastAPI application (Python 3.11+, SQLAlchemy, PostgreSQL, JWT auth) |
| [`backend/app/routers/`](backend/app/routers) | API endpoints: products, sales, customers, layaways, catalog, upload, auth |
| [`backend/app/models.py`](backend/app/models.py) | SQLAlchemy ORM schema (11 tables) |
| [`backend/app/auth.py`](backend/app/auth.py) | Authn/authz: JWT, refresh-token rotation, ``ROLE_PERMISSIONS`` |
| [`backend/docs.html`](backend/docs.html) | Generated API reference (``/api/docs``) — see `[docs/api-reference.md](docs/api-reference.md)` |
| [`backend/tests/`](backend/tests) | Pytest suite incl. docs-drift guards |
| [`frontend/`](frontend) | React SPA (Vite): Productos / Apartados / Administración / Perfil tabs |
| [`scripts/`](scripts) | Occasional maintenance utilities — see [scripts/README.md](scripts/README.md) |
| [`scripts/deploy.sh`](scripts/deploy.sh) | GCP deploy master; steps: [`deploy-setup-infra.sh`](scripts/deploy-setup-infra.sh), [`deploy-build-push.sh`](scripts/deploy-build-push.sh), [`deploy-cloud-run.sh`](scripts/deploy-cloud-run.sh) |
| ``docker-compose*.yml`` | Dev / Pi / Cloud-Run compose definitions |
| [`Dockerfile`](backend/Dockerfile) | Backend multi-target build (``base``, ``backend-dev``, ``backend-prod``, ``backend-pi``) |
| [`scripts/backup.sh`](scripts/backup.sh), [`scripts/restore.sh`](scripts/restore.sh) | PostgreSQL + uploads backup / restore |
| [`docs/`](docs) | Technical (EN), business (ES), user guides (ES), and flows (ES) |
| [`docs/card-mockup.html`](docs/card-mockup.html) | Static mockup that the PDF/HTML catalog rendering mirrors |

## Quick start (local dev)

```bash
docker compose up --build        # backend :3001, frontend :5173, postgres :5432
```

Non-Docker equivalent:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export JWT_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))")
python -m seed                      # categories, colors, roles, admin user
uvicorn app.main:app --reload --port 3001
```

Default admin credentials come from ``DEFAULT_ADMIN_PASSWORD`` (see
[`backend/.env.example`](backend/.env.example)). Full setup details: [docs/technical/quickstart.md](docs/technical/quickstart.md).

## Documentation — where to look

**Technical (English) — for developers / operators**
- Overview & architecture — [docs/technical/overview.md](docs/technical/overview.md), [architecture.md](docs/technical/architecture.md)
- Deployment — [docs/technical/deployment.md](docs/technical/deployment.md)
- Database schema — [docs/technical/database.md](docs/technical/database.md)
- Auth & security — [docs/technical/auth-security.md](docs/technical/auth-security.md)
- Testing — [docs/technical/testing.md](docs/technical/testing.md)
- API reference — [docs/api-reference.md](docs/api-reference.md)

**Business rules & operations (Español)**
- Índice — [docs/business/index.md](docs/business/index.md)

**User guides (Español)**
- Guías por rol — [docs/user-guides/index.md](docs/user-guides/index.md)

**Flows (Español, diagramas)**
- Flujos — [docs/flows/index.md](docs/flows/index.md)

Start here: [docs/index.md](docs/index.md).

## Languages in this repo

- Code identifiers, comments, and commit messages: English.
- Runtime API error messages and frontend UI copy: Spanish.
- Bug reports / issues: Spanish preferred.

## Docs ↔ code drift protection

`[docs/api-reference.md](docs/api-reference.md)` is the single source of truth for the public API. A
build script renders it to [`backend/docs.html`](backend/docs.html) (served at ``/api/docs``), and
two pytest guards keep everything honest:

- [`backend/tests/test_docs_permissions.py`](backend/tests/test_docs_permissions.py) — the permission matrix in the API
  reference must equal ``app.auth.ROLE_PERMISSIONS``.
- [`backend/tests/test_docs_generated.py`](backend/tests/test_docs_generated.py) — regenerating [`backend/docs.html`](backend/docs.html)
  must produce a byte-identical file.