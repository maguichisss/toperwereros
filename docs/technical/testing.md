# Testing

Backend tests live in [`backend/tests/`](../../backend/tests) and run with **pytest** against an
**in-memory SQLite** database per session (see [`conftest.py`](../../backend/tests/conftest.py)). The FastAPI app
is exercised through `httpx`'s `TestClient`; `JWT_SECRET` is set to a fixed
test value and admin/employee fixtures ship pre-authenticated tokens.

```sh
cd backend
pytest -q              # full suite
pytest -k docs         # documentation drift guards only
pytest tests/test_sales.py -q
```

## What the suite covers

| File | Focus |
| --- | --- |
| [`test_auth.py`](../../backend/tests/test_auth.py) | Login, refresh rotation, logout, profiles, admin user CRUD, lockout |
| [`test_auth_middleware.py`](../../backend/tests/test_auth_middleware.py) | Permission enforcement on routes, 401/403 behavior |
| [`test_catalog.py`](../../backend/tests/test_catalog.py) | PDF/HTML catalog generation, themes, ordering, filters |
| [`test_categories.py`](../../backend/tests/test_categories.py) / [`test_colors.py`](../../backend/tests/test_colors.py) | CRUD + uniqueness / hex validation |
| [`test_config.py`](../../backend/tests/test_config.py) | Config helpers (`safe_upload_path`, `escape_like`, image detection) |
| [`test_customers.py`](../../backend/tests/test_customers.py) | Customer CRUD, name/phone search |
| [`test_layaways.py`](../../backend/tests/test_layaways.py) | Layaway lifecycle: create, pay, cancel, complete → sale |
| [`test_products.py`](../../backend/tests/test_products.py) | Product CRUD, search, filtering, pagination, stock |
| [`test_sales.py`](../../backend/tests/test_sales.py) | Sale creation, atomic stock decrement, list/get |
| [`test_schemas.py`](../../backend/tests/test_schemas.py) | Pydantic validation rules |
| [`test_upload.py`](../../backend/tests/test_upload.py) | Magic-byte validation, size cap, path safety |
| [`test_docs_permissions.py`](../../backend/tests/test_docs_permissions.py) | Drift guard: permission matrix ⇔ `ROLE_PERMISSIONS` |
| [`test_docs_generated.py`](../../backend/tests/test_docs_generated.py) | Drift guard: regenerated [`docs.html`](../../backend/docs.html) ⇔ committed file |

## Documentation drift guards

The public API is documented from a single source of truth —
[`docs/api-reference.md`](../api-reference.md) — rendered to [`backend/docs.html`](../../backend/docs.html) by
[`backend/scripts/gen_api_docs.py`](../../backend/scripts/gen_api_docs.py) (adds a dev-only `markdown` dependency to
[`requirements-dev.txt`](../../backend/requirements-dev.txt)). Two tests keep everything consistent:

1. **[`test_docs_permissions.py`](../../backend/tests/test_docs_permissions.py)** — the permission matrix embedded in
   [`api-reference.md`](../api-reference.md) must exactly match `app.auth.ROLE_PERMISSIONS`. Edit
   either side and re-read this test.
2. **[`test_docs_generated.py`](../../backend/tests/test_docs_generated.py)** — running the generator must reproduce the
   committed [`backend/docs.html`](../../backend/docs.html) byte-for-byte. After editing
   [`api-reference.md`](../api-reference.md), regenerate and commit the HTML:

```sh
cd backend
python scripts/gen_api_docs.py        # writes backend/docs.html
pytest tests/test_docs_generated.py -q
```

## CI

[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) runs a `test` job (Python 3.13, cached pip,
`pytest tests/ -q`) for every push. Only the *default branch* push triggers
`build-and-deploy`, and only after tests pass — so the drift guards gate every
production deploy.

## Notes on test speed & isolation

- SQLite (not Postgres) keeps the suite fast and hermetic; PG-specific
  features (ILIKE, casting) are exercised via SQLAlchemy-level behavior, with
  the real PG behavior covered manually on dev/Pi/Cloud.
- Foreign keys are enabled per-connection via `PRAGMA foreign_keys=ON`.