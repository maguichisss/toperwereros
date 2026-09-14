# Store Catalog API Reference

> This document is the **single source of truth** for the public API contract.
> It is rendered into [`backend/docs.html`](../backend/docs.html) by [`backend/scripts/gen_api_docs.py`](../backend/scripts/gen_api_docs.py)
> and served at `/docs`. Two pytest guards ([`test_docs_permissions.py`](../backend/tests/test_docs_permissions.py),
> [`test_docs_generated.py`](../backend/tests/test_docs_generated.py)) keep it in sync with the code.
> Interactive schemas: `/swagger` (OpenAPI) · `/redoc` · `/openapi.json`.

## Overview

FastAPI backend for Toperwereros: authentication (JWT), product catalog,
categories, colors, image upload, PDF catalog generation, sales (POS),
customers, and layaways (apartados). Every endpoint except `POST /api/auth/login`
requires a JWT Bearer token. Response/error messages are in Spanish.

**Stats** — Endpoints: **46** · Modules: **9** · Roles: **3** ·
Employee permissions: **15**

<!-- API-META: {"endpoints":46,"modules":9,"roles":3,"permissions":15} -->

## Authentication

All endpoints except `POST /api/auth/login` require:

```
Authorization: Bearer <access_token>
```

| Setting | Value |
| --- | --- |
| Token format | JWT, algorithm HS256 |
| Access-token expiry | `JWT_EXPIRE_MINUTES` (default `1440` = 24 h) |
| Refresh-token expiry | `REFRESH_TOKEN_EXPIRE_DAYS` (default `7`) |
| Secret | `JWT_SECRET` env var (**required** at startup; sample in `.env.example`) |
| Password hashing | bcrypt (`passlib`) |
| Login lockout | 5 failed attempts → locked for `LOCKOUT_DURATION_MINUTES` (15) |

Refresh tokens are opaque, stored by SHA-256 hash with family tracking
(rotation + family revoke on reuse). `POST /api/auth/refresh` exchanges a valid
refresh token for a new access+refresh pair (the old one is revoked).

## Roles & Permissions

| Role | Level | Capabilities |
| --- | --- | --- |
| `admin` | `*` (wildcard) | Full access to all endpoints, including user/role management |
| `employee` | 15 permissions | Products (CRUD), sales (view/create), layaways (view/create/edit), customers (CRUD), categories (view), colors (view) |
| `viewer` | 6 permissions | Read-only: products, sales, layaways, customers, categories, colors |

### Permission matrix (machine-readable source)

This block is authoritative for the permission drift test — it must equal
`app.auth.ROLE_PERMISSIONS`.

<!-- ROLES:START -->
```json
{"admin": ["*"], "employee": ["product.view", "product.create", "product.edit", "product.delete", "sale.view", "sale.create", "apartado.view", "apartado.create", "apartado.edit", "customer.view", "customer.create", "customer.edit", "customer.delete", "category.view", "color.view"], "viewer": ["product.view", "sale.view", "apartado.view", "customer.view", "category.view", "color.view"]}
```
<!-- ROLES:END -->

### Permission matrix (human-readable)

| Permission | admin | employee | viewer |
| --- | :-: | :-: | :-: |
| `product.view` | ✓ | ✓ | ✓ |
| `product.create` | ✓ | ✓ | |
| `product.edit` | ✓ | ✓ | |
| `product.delete` | ✓ | ✓ | |
| `sale.view` | ✓ | ✓ | ✓ |
| `sale.create` | ✓ | ✓ | |
| `apartado.view` | ✓ | ✓ | ✓ |
| `apartado.create` | ✓ | ✓ | |
| `apartado.edit` | ✓ | ✓ | |
| `customer.view` | ✓ | ✓ | ✓ |
| `customer.create` | ✓ | ✓ | |
| `customer.edit` | ✓ | ✓ | |
| `customer.delete` | ✓ | ✓ | |
| `category.view` | ✓ | ✓ | ✓ |
| `category.create` / `category.edit` / `category.delete` | ✓ | | |
| `color.view` | ✓ | ✓ | ✓ |
| `color.create` / `color.edit` / `color.delete` | ✓ | | |
| `user.manage` | ✓ | | |

Admin bypasses all checks via the `*` wildcard; permission strings may also be
matched by a `.*` parent (e.g. a role holding `product.*` satisfies
`product.view`).

## Endpoint Reference

### Auth — `/api/auth`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | public | Authenticate; returns `access_token` + `refresh_token`. Rate-limited 5/min/IP. |
| POST | `/api/auth/refresh` | refresh token | Rotate tokens. Rate-limited 10/min/IP. |
| POST | `/api/auth/logout` | authenticated | Revoke all refresh tokens for the user. |
| GET | `/api/auth/me` | authenticated | Current user profile (id, username, email, role, avatar). |
| GET | `/api/auth/roles` | `user.manage` | List roles ordered by id. |
| POST | `/api/auth/roles` | `user.manage` | Create role (name lowered, unique). Rate-limited via register bucket. |
| POST | `/api/auth/change-password` | authenticated | Change own password (min 4 chars); revokes all sessions. Rate-limited 1/min/IP. |
| PATCH | `/api/auth/profile` | authenticated | Update own `email` and/or `image_url` (email uniqueness enforced). |
| POST | `/api/auth/avatar` | authenticated | Upload avatar (JPEG/PNG/WebP, ≤ 5 MB); deletes previous. Rate-limited 3/min/IP. |
| GET | `/api/auth/users` | `user.manage` | List all users ordered by username. |
| POST | `/api/auth/register` | `user.manage` | Create user (unique username/email lowercased). Rate-limited 5/min/IP. |
| PUT | `/api/auth/users/{user_id}` | `user.manage` | Update user fields; cannot change own role or deactivate self. |
| PATCH | `/api/auth/users/{user_id}/active` | `user.manage` | Toggle active/disabled; cannot deactivate self. |

### Products — `/api/products`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/products` | `product.view` | Paginated list (only `stock > 0`). Query: `q` (search), `category_ids`, `page` (≥1), `per_page` (1–200, default 20), `export` (skip pagination). Search matches code, name, ubicacion, price, category name, color name (ILIKE, escaped). |
| GET | `/api/products/{product_id}` | `product.view` | Single product with categories and colors. |
| POST | `/api/products` | `product.create` | Create product: unique code, name/code required, price ≥ 0, referenced categories/colors must exist. |
| PUT | `/api/products/{product_id}` | `product.edit` | Full update; replaces categories/colors; deletes the old image file when `image_url` changes. |
| DELETE | `/api/products/{product_id}` | `product.delete` | Delete product and its image file (204). |

### Categories — `/api/categories`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/categories` | `category.view` | List all categories (alphabetical). |
| POST | `/api/categories` | `category.create` | Create category (name unique, lowered). |
| PUT | `/api/categories/{category_id}` | `category.edit` | Update category name. |
| DELETE | `/api/categories/{category_id}` | `category.delete` | Delete; **409** if assigned to any product. |

### Colors — `/api/colors`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/colors` | `color.view` | List all colors (alphabetical). |
| POST | `/api/colors` | `color.create` | Create color; `hex` must match `#RRGGBB`, name unique and lowered. |
| PUT | `/api/colors/{color_id}` | `color.edit` | Update name and/or hex. |
| DELETE | `/api/colors/{color_id}` | `color.delete` | Delete; **409** if assigned to any product. |

### Upload — `/api/upload`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/upload` | `product.edit` | Upload product image. Magic bytes (JPEG/PNG/WebP), ≤ 5 MB, ≥ 8 bytes. Returns `{"image_url": "/uploads/<uuid>.<ext>"}`. Rate-limited 5/min/IP. |

### Catalog — `/api/catalog`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/catalog/pdf` | `product.view` | Generate PDF (default) or HTML catalog. Only in-stock products. Query: `ids` (comma ints), `q` (search), `format` (`pdf`\|`html`), `theme`. Ordering and themes documented under Business Rules. |

### Sales — `/api/sales`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/sales` | `sale.view` | Paginated list, newest first, with line items and creator name. Query: `page` (≥1), `per_page` (1–100, default 20), `start_date`, `end_date` (`YYYY-MM-DD`, inclusive). |
| GET | `/api/sales/{sale_id}` | `sale.view` | Single sale with all line items. |
| POST | `/api/sales` | `sale.create` | Create sale. At least one item, atomic stock decrement via savepoint, unit price captured from product at sale time, `created_by` = authenticated user. |

### Customers — `/api/customers`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/customers` | `customer.view` | List customers; `q` matches `name` or `phone` (ILIKE); ordered by name. |
| GET | `/api/customers/{customer_id}` | `customer.view` | Single customer. |
| POST | `/api/customers` | `customer.create` | Create customer (name required; phone/email/notes optional). |
| PUT | `/api/customers/{customer_id}` | `customer.edit` | Update customer fields. |
| DELETE | `/api/customers/{customer_id}` | `customer.delete` | Delete customer (204). |

### Layaways (apartados) — `/api/layaways`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/layaways` | `apartado.create` | Create layaway. Provide `customer_id` **or** inline `customer` (not both/neither). Deposit > 0 and ≤ total; locks in prices, decrements stock; deposit recorded as first payment. |
| GET | `/api/layaways` | `apartado.view` | Paginated list, newest first. Query: `status` (`active`\|`completed`\|`cancelled`), `customer_id`, `page`, `per_page` (1–100). |
| GET | `/api/layaways/{layaway_id}` | `apartado.view` | Single layaway with items, payments, customer, creator, linked `sale_id`. |
| PATCH | `/api/layaways/{layaway_id}` | `apartado.edit` | Update `notes` on an active layaway. |
| POST | `/api/layaways/{layaway_id}/payments` | `apartado.edit` | Add payment: positive and ≤ balance; auto-completes (creates linked Sale) when balance hits $0. |
| POST | `/api/layaways/{layaway_id}/items` | `apartado.edit` | Add item to active layaway; locks current price, decrements stock, recalculates total/balance. |
| DELETE | `/api/layaways/{layaway_id}/items/{item_id}` | `apartado.edit` | Remove item from active layaway; restores stock; must keep ≥ 1 item; new total must not drop below payments made. |
| PUT | `/api/layaways/{layaway_id}/items/{item_id}` | `apartado.edit` | Change item quantity (≥ 1); delta-adjusts stock; same payments floor rule. |
| PATCH | `/api/layaways/{layaway_id}/cancel` | `apartado.edit` | Cancel active layaway; restores all stock; payments history retained. |
| PATCH | `/api/layaways/{layaway_id}/complete` | `apartado.edit` | Manually complete active layaway; creates linked Sale (idempotent). |

## Business Rules

### Products

- `code` is globally unique (enforced on create **and** update; error names the conflicting product).
- `name`, `code`, and `price` required; `price ≥ 0`.
- All referenced `category_ids` / `color_ids` must exist (count validated).
- List endpoint always filters `stock > 0`; stock can still dip to 0 via sell-through.
- Old image file is deleted on image change (update) and on delete.
- Search = case-insensitive ILIKE across code, name, ubicacion, price (`cast` to text), category name, and color name; `%`, `_`, `\` are escaped.

### Sales

- At least one item required: `"La venta debe tener al menos un artículo"`.
- Each product must exist (404) and have sufficient stock (400).
- `unit_price` comes from the product **at sale time**, never from the request; `total` is computed server-side.
- Stock decrement + sale creation wrap in a SQLAlchemy **savepoint** (`db.begin_nested()`): any failure → no partial sale, no stock change.
- Sales are immutable: no delete/update endpoints.

### Layaways (apartados)

- Exactly one of `customer_id` / inline `customer`.
- `deposit > 0` and `deposit ≤ total`; initial deposit recorded as first `LayawayPayment`.
- Each item locks the current `unit_price` and **decrements stock** at creation.
- Payments only on `active` layaways; `amount > 0` and `amount ≤ balance`.
- Payment that brings `balance` to $0 **auto-completes**: creates a linked `Sale` with the locked prices (no second stock decrement).
- Manual `complete` is idempotent (no-op if `sale_id` already set); any remaining positive balance is recorded as a final payment and zeroed.
- Edit notes / add / remove / quantity-change / cancel only on `active` layaways.
- Remove item → restores stock, must keep ≥ 1 item.
- Quantity change → delta stock adjustment (increase decrements, decrease restores).
- Remove/quantity-decrease blocked when the new total would fall below total payments.
- Cancel → restores all stock, status `cancelled`, payments history retained.

### Image uploads

- Endpoints: `POST /api/upload` (products) and `POST /api/auth/avatar` (profiles).
- Validation by **magic bytes**, not Content-Type/extension.
- Formats: JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), WebP (`52 49 46 46`).
- Max 5 MB, min 8 bytes; random UUID filenames; extension derived from detected type.
- Stored to local `uploads/` or GCS (`GCS_BUCKET`); `safe_upload_path` blocks traversal.

### PDF catalog

- Only in-stock products (`stock > 0`); optional `ids` and `q` filters.
- Ordering: the first **64** products are the newest (by `created_at`, descending); the rest sort by category product-count (desc), category name, color name, then stock (uncategorized last).
- 4-column × 4-row card grid = **16 products/page** (A4).
- Each card: center-cropped image (40×48 mm @ 72 DPI, JPEG q85) or an initial-letter placeholder, name (truncated to ~2 lines), and a price band with the code.
- Weekly header on every page: `Válido de {lunes} a {domingo} | semana {N}` (Spanish month names, ISO week number, based on today).
- Themes: `classic`, `nocturno`, `kraft`, `elegante`, `marino`, `sol`, `cyber`, `vino`, `rosa`, `arcoiris`, `nebulosa`, `triangulos`, `olas`, `mandala`, `aurora`, `confeti`, `galaxia`, `marco`, `flores`.
- Output: PDF (attachment) or HTML (inline); `format`/`theme`/`ids` validation errors are 400.
- Layout mirrors [`docs/card-mockup.html`](card-mockup.html).

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/store_catalog` | SQLAlchemy connection string |
| `JWT_SECRET` | *(required)* | HS256 signing key (sample in `.env.example`) |
| `JWT_EXPIRE_MINUTES` | `1440` | Access-token lifetime (minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh-token lifetime (days) |
| `LOCKOUT_MAX_ATTEMPTS` | `5` | Failed logins before lockout |
| `LOCKOUT_DURATION_MINUTES` | `15` | Lockout window |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `DEFAULT_ADMIN_PASSWORD` | `admin123` | Seed password for default admin ([`seed.py`](../backend/seed.py)) |
| `GCS_BUCKET` | *(empty)* | Set to store uploads in Google Cloud Storage |
| `GCP_PROJECT` | *(empty)* | GCP project id (GCS / Cloud SQL only) |
| `CLOUD_SQL_CONNECTION_STRING` | *(empty)* | Starts the embedded Cloud SQL Auth Proxy |

Full deployment context: [`docs/technical/deployment.md`](technical/deployment.md).

## Rate Limits

Applied via slowapi, keyed per authenticated user (`user:{id}`) or client IP:

| Endpoint | Limit |
| --- | --- |
| `POST /api/auth/login` | 5 / minute |
| `POST /api/auth/refresh` | 10 / minute |
| `POST /api/auth/change-password` | 1 / minute |
| `POST /api/auth/avatar` | 3 / minute |
| `POST /api/auth/register` | 5 / minute |
| `POST /api/upload` | 5 / minute |

Exceeding a limit returns `429 Too Many Requests`.

## Error Responses

All errors return JSON with a `detail` field (array for 422).

| Status | Meaning |
| --- | --- |
| `400` | Validation error (bad input, duplicate code, insufficient stock, etc.) |
| `401` | Not authenticated / invalid or expired token |
| `403` | Authenticated but lacking the required permission |
| `404` | Resource not found |
| `409` | Conflict (duplicate name, category/color in use) |
| `422` | Request validation (malformed body) |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

## Service endpoints (not in OpenAPI)

- `GET /docs` — this reference as HTML (rendered from this Markdown).
- `GET /redoc` — ReDoc UI (pinned v2.1.5).
- `GET /api/health` — `{"status": "ok", "db": "connected"}`; **503** when the database is unreachable (used by Cloud Run probes).

---

*Maintenance: edit this file, then run `python scripts/gen_api_docs.py` from
[`backend/`](../backend) and commit the regenerated [`backend/docs.html`](../backend/docs.html).*