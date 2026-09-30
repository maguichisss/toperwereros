# store-catalog — Agent Guide

Catálogo de tienda (punto de venta): backend FastAPI + frontend React/Vite,
deploy Docker Compose (dev / Pi QA / Cloud Run GCP). Contexto para agentes de código.

## Comandos de verificación

- Backend (pytest NO lee `backend/.env`; `JWT_SECRET` es obligatorio):
  `cd backend && JWT_SECRET=test-secret pytest tests/ -q`
- Test puntual: `cd backend && JWT_SECRET=test-secret pytest tests/test_catalog.py::TestCustomPDFConfig -q`
- Frontend (no hay lint; el gate es el build): `cd frontend && npm run build`
- Docs (cero drift: se generan desde el código, jamás se editan a mano):
  `bash scripts/generate_docs.sh --all` y luego `bash scripts/generate_docs.sh --check`
- Links de docs: `python scripts/check-doc-links.py`

## Estructura

- `backend/app/` FastAPI: `main.py`, `routers/` (catalog, auth, sales, layaways,
  customers, products…), `models.py` (SQLAlchemy), `schemas.py` (Pydantic),
  `auth.py` (bcrypt, JWT, `ROLE_PERMISSIONS`), `config.py`, `query_filters.py`
  (DSL `PRODUCT_FIELDS`, `fetch_page` compartido para listas paginadas),
  `database.py`, `gcs.py`, `i18n.py` (traducción de
  errores ES/EN vía `Accept-Language`).
- `backend/alembic/` migraciones (naming `<hash>_<desc>.py`).
- `frontend/src/` React: `components/`, `context/AuthContext.jsx`, `api/client.js`, `utils.js`.
- `scripts/` utilidades de operación (ver [`scripts/README.md`](scripts/README.md)).
- `docs/` comportamiento (ES en `business/`) y técnica (EN en `technical/`);
  [`docs/api-reference.md`](docs/api-reference.md) es generado.

## Fuentes de verdad

- API + matriz de permisos (generadas del código):
  [`docs/api-reference.md`](docs/api-reference.md)
- Comportamiento (ES): `docs/business/` · Técnica (EN): `docs/technical/`
  (p. ej. [`docs/technical/deployment.pi.md`](docs/technical/deployment.pi.md))
- Scripts de operación: [`scripts/README.md`](scripts/README.md)
- Migraciones: `backend/alembic/versions/` (naming `<hash>_<desc>.py`)

## Convenciones de API

- Listas paginadas → `{"<items>": [...], "total": N}` (p. ej. `ProductListResponse`).
  `GET /api/products?export=true` omite paginación y responde
  `{"products": [...], "total": N}`.
- Paginación: `page`/`per_page` (o `skip`/`limit`).
- Query DSL (filtros) en `backend/app/query_filters.py` (`PRODUCT_FIELDS`,
  `CUSTOMER_FIELDS`, `SALE_FIELDS`, `LAYAWAY_FIELDS`). Operadores
  (`query_filters.py`): `__eq`, `__ne`, `__gt`, `__gte`, `__lt`, `__lte`,
  `__like`, `__contains`, `__startswith`, `__endswith`, `__not_like`, `__in`,
  `__not_in`, `__is_null`. Relaciones M2M (solo products): `category__…`,
  `color__…` (claves `category`/`color`, resuelven vía
  `Product.categories/colors.any(Category.name/Color.name…)`).
- **No inventar params/filtros**: añadirlos como `FieldSpec` antes de usarlos.
- Proyección: `modo=basico|detallado` + `campos=a,b` (`PRODUCT_BASIC =
  id, code, name, price, stock, ubicacion`).
- Mensajes de error en **inglés canónico** en el backend y traducidos a español
  vía `Accept-Language: es` por `app/i18n.py` (error + 422). Todo mensaje de
  `HTTPException`/`detail` debe tener su traducción en `i18n.py` (guárdalo con
  `tests/test_i18n.py`); 401 con header `WWW-Authenticate: Bearer`. El frontend
  siempre envía `Accept-Language: es-MX` (UI en español).

## Convenciones

- **Sin comentarios** en código salvo que se pida explícitamente.
- Backend: docstrings estilo Google; commits en inglés plano (sin prefijos conventional).
- **El código es la fuente única de verdad.** Al tocar endpoints/permisos se regeneran
  docs; matriz de permisos (atómica, sin compuestos) en `docs/api-reference.md`,
  `ROLE_PERMISSIONS` en `backend/app/auth.py`. Nunca comitear secretos.

## Tests (backend)

Fixtures en `backend/tests/conftest.py`:
`db`, `_roles`, `admin_user`, `employee_user`, `viewer_user`,
`admin_token`, `employee_token`, `viewer_token`,
`admin_headers`, `employee_headers`, `viewer_headers`, `client`.

- Suite: `cd backend && JWT_SECRET=test-secret pytest tests/ -q`
- Área/puntual: `tests/test_x.py` · `tests/test_x.py::TestClase::test_metodo` · `-k "patron"`
- pytest NO lee `backend/.env`.
- Guard de i18n: `tests/test_i18n.py` falla si hay mensajes de `detail` en
  español, sin traducción o con f-strings sin patrón registrado en `i18n.py`.
- Los writes sale/layaway tienen rate limit 20/min (slowapi, clave = user id o IP);
  `conftest._setup_db` resetea el storage de limiters entre tests (no encadenar
  >20 POSTs en un mismo test).
- Config pytest en `backend/pyproject.toml` (silencia el `UnsupportedFieldAttributeWarning`
  de pydantic; pytest NO lee `backend/.env`).

## Migraciones (alembic)

- Modelos en `app/models.py`; migraciones a mano en `backend/alembic/versions/`
  con `revision`/`down_revision` encadenado al hash previo y nodos `op.*`
  (ver `b2c3d4e5f6g7_add_refresh_tokens.py` como plantilla).
- Aplicar/validar: `alembic upgrade head` (el entrypoint lo ejecuta al boot).
  El boot hace `Base.metadata.create_all` (modelos) y luego `alembic upgrade head`;
  la cadena alembic es solo incremental y no bootstrapea una BD vacía por sí sola.
- Seed idempotente `backend/seed.py`: categorías, colores, roles, admin.

## Agentes y cuándo pedirles ayuda

| Agente | Úsalo cuando… |
| --- | --- |
| `@docs-sync` | tocaste API/permisos o quieres sincronizar/verificar docs |
| `@backend-tester` | correr la suite/tests o investigar un test rojo |
| `@backend-dev` | implementar/arreglar backend |
| `@frontend-dev` | tareas de UI / validar build frontend |
| `@db-helper` | esquema, migraciones, inspección psql, backup/restore |
| `@security-auditor` | revisiones de seguridad/auth/permisos |
| `@deploy-ops` | despliegues Pi/GCP, env, ops |
| `@reviewer` | revisar un diff antes de commitear |
| `@commit` | revisar el working tree, clasificar cambios por área, proponer mensaje y commitear tras aprobación con "daleee" |

### Flujo automático por área

Ante cada cambio solicitado se delega al agente del área (los triviales, ya
cubiertos por contexto, se editan directo). Cada subagente inicia contexto
limpio: pasarle el mínimo contexto del cambio en el prompt. No se lanzan todos
los agentes — solo el(s) del área del cambio.

| Área del cambio | Agente |
| --- | --- |
| Backend (routers, modelos, schemas, permisos, query_filters) | `@backend-dev` |
| Frontend/UI (componentes, auth, cliente API, build) | `@frontend-dev` |
| Esquema, migraciones, psql, backup/restore | `@db-helper` |
| Auth/permisos/seguridad | `@security-auditor` |
| Tras tocar backend | `@backend-tester` para verificar |
| API o permisos tocados / docs sincronización | `@docs-sync` |
| Antes de commitear | `@reviewer` (diff, secretos, cero drift) y `@commit` en Fase 1 (clasificar + mensaje) |

- El commit real **solo** tras aprobación explícita con "daleee" (nunca auto-commitear).
- La verificación de cierre sigue la sección «Verificación antes de cerrar un cambio».

## Capas de entorno

- `./.env` raíz: solo interpolación de Docker Compose (la app NO la lee).
- `backend/.env` (dev) / `.env.pi` (Pi) / `.env.prod` (GCP): entorno de la app vía
  `env_file`; `DATABASE_URL` lo inyecta compose. `.env*` y `secrets/` gitignored.
- `JWT_SECRET` es obligatorio en runtime.

## Verificación antes de cerrar un cambio

1. Backend: `pytest` (suite completa o del área tocada).
2. Frontend: `npm run build` (solo el warning conocido de chunk size).
3. Docs: `bash scripts/generate_docs.sh --check` pasa y
   `python scripts/check-doc-links.py` reporta todos los links OK, sin editar
   artefactos a mano.
4. Cambios funcionales traen/ajustan tests.
5. Seguridad: sin secretos en código/logs/commits; permisos coherentes con
   `ROLE_PERMISSIONS` y la matriz en `docs/api-reference.md`.