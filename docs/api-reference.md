# Store Catalog API Reference

> This document is the **single source of truth** for the public API contract.
> It is rendered into [`backend/docs.html`](../backend/docs.html) by [`scripts/generate_docs_html.py`](../scripts/generate_docs_html.py)
> and served at `/docs`. Two pytest guards ([`test_docs_permissions.py`](../backend/tests/test_docs_permissions.py),
> [`test_docs_generated.py`](../backend/tests/test_docs_generated.py)) keep it in sync with the code.
> Interactive schemas: `/swagger` (OpenAPI) · `/redoc` · `/openapi.json`.

## Overview

FastAPI backend for Toperwereros: authentication (JWT), product catalog,
categories, colors, image upload, PDF catalog generation, sales (POS),
customers, and layaways (apartados). Every endpoint except `POST /api/auth/login`
requires a JWT Bearer token. Response/error messages are in Spanish.

<!-- API-META: {"endpoints": 49, "modules": 11, "roles": 3, "permissions": 21} -->

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
| Login lockout | 5 failed attempts -> locked for `LOCKOUT_DURATION_MINUTES` (15) |

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

This block is authoritative for the permission drift test -- it must equal
`app.auth.ROLE_PERMISSIONS`.

<!-- ROLES:START -->
```json
{"admin":["*"],"employee":["product.view","product.create","product.edit","product.delete","sale.view","sale.create","apartado.view","apartado.create","apartado.edit","customer.view","customer.create","customer.edit","customer.delete","category.view","color.view"],"viewer":["product.view","sale.view","apartado.view","customer.view","category.view","color.view"]}
```
<!-- ROLES:END -->

### Permission matrix (human-readable)

| Permission | admin | employee | viewer |
| --- | :-: | :-: | :-: |
| `apartado.create` | ✓ | ✓ |  |
| `apartado.edit` | ✓ | ✓ |  |
| `apartado.view` | ✓ | ✓ | ✓ |
| `category.view` | ✓ | ✓ | ✓ |
| `color.view` | ✓ | ✓ | ✓ |
| `customer.create` | ✓ | ✓ |  |
| `customer.delete` | ✓ | ✓ |  |
| `customer.edit` | ✓ | ✓ |  |
| `customer.view` | ✓ | ✓ | ✓ |
| `product.create` | ✓ | ✓ |  |
| `product.delete` | ✓ | ✓ |  |
| `product.edit` | ✓ | ✓ |  |
| `product.view` | ✓ | ✓ | ✓ |
| `sale.create` | ✓ | ✓ |  |
| `sale.view` | ✓ | ✓ | ✓ |

Admin bypasses all checks via the `*` wildcard; permission strings may also be
matched by a `.*` parent (e.g. a role holding `product.*` satisfies
`product.view`).

### Permission inventory & coverage

Computed from the live routes and `ROLE_PERMISSIONS`; enforced by
[`test_route_permissions.py`](../backend/tests/test_route_permissions.py).

```text
Permission Coverage Report
==================================================
Total routes analyzed:    49
  Public:                 2
  With permission:        40
  Authenticated only:     5
  (allowlisted):          5
  (violations):           0

Permissions:
  In inventory (declared ∪ explicit): 23
  Declared on routes:                 23
  Undefined (not in inventory):       0
  Truly unused:                       0
  Admin-only (wildcard):              8

Coverage Tiers:
  ✅ Explicitly assigned:    15   (explicitly given to employee/viewer)
  🔑 Admin-only (wildcard):   8   (only admin reaches them)
  ❌ Truly unused:            0   (not declared anywhere)

Total: 23 = 15 + 8 + 0
```

## Endpoint Reference

### Auth -- `/api/auth`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/avatar` | public | Upload a profile avatar image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit. Rate-limited to 3 attempts per minute per IP. |
| POST | `/api/auth/change-password` | public | Change the authenticated user's password. New password must be at least 4 characters. Rate-limited to 1 attempt per minute per IP. |
| POST | `/api/auth/login` | public | Authenticate with username/password and receive a JWT token. Rate-limited to 5 attempts per minute per IP. |
| POST | `/api/auth/logout` | public | Revoke all refresh tokens for the authenticated user. |
| GET | `/api/auth/me` | public | Return the authenticated user's profile including id, username, email, role, and avatar. |
| PATCH | `/api/auth/profile` | public | Update own email and/or avatar URL. Email uniqueness is enforced across users. |
| POST | `/api/auth/refresh` | public | Exchange a valid refresh token for a new access+refresh token pair. Old refresh token is revoked (rotation). |
| POST | `/api/auth/register` | `user.manage` | Create a new user account. Username and email must be unique. Requires admin (user.manage) permission. Rate-limited to 5 attempts per minute per IP. |
| GET | `/api/auth/roles` | `user.manage` | Return all roles. Requires admin (user.manage) permission. |
| POST | `/api/auth/roles` | `user.manage` | Create a new role. Requires admin (user.manage) permission. |
| GET | `/api/auth/users` | `user.manage` | Return all users ordered by username. Requires admin (user.manage) permission. |
| PUT | `/api/auth/users/{user_id}` | `user.manage` | Admin-only. Update username, email, role, password, or active status of a user. |
| PATCH | `/api/auth/users/{user_id}/active` | `user.manage` | Enable or disable a user account. Admin only. Cannot deactivate yourself. |

### Products -- `/api/products`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/products` | `product.view` | Paginated product list with full-text search (code, name, ubicacion, price, category, color), category filtering, and export mode. |
| POST | `/api/products` | `product.create` | Create a new product. Requires unique code, valid price (>= 0), and existing category/color IDs. |
| GET | `/api/products/{product_id}` | `product.view` | Return a single product by ID with categories and colors loaded. |
| PUT | `/api/products/{product_id}` | `product.edit` | Full product update. Old image file is deleted from disk when image_url changes. |
| DELETE | `/api/products/{product_id}` | `product.delete` | Delete a product and remove its image file from disk. |

### Categories -- `/api/categories`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/categories` | `category.view` | Return all categories ordered alphabetically. |
| POST | `/api/categories` | `category.create` | Create a new category. Name must be non-empty and unique. |
| PUT | `/api/categories/{category_id}` | `category.edit` | Update a category's name. New name must be unique. |
| DELETE | `/api/categories/{category_id}` | `category.delete` | Delete a category. Blocked with 409 if the category is assigned to any product. |

### Colors -- `/api/colors`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/colors` | `color.view` | Return all colors ordered alphabetically. |
| POST | `/api/colors` | `color.create` | Create a new color. Name must be unique. Hex must match #RRGGBB format. |
| PUT | `/api/colors/{color_id}` | `color.edit` | Update a color's name and hex code. Both must be valid and unique. |
| DELETE | `/api/colors/{color_id}` | `color.delete` | Delete a color. Blocked with 409 if the color is assigned to any product. |

### Upload -- `/api/upload`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/upload` | `product.edit` | Upload a product image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit. Returns the URL path; link to a product via PUT /api/products/{id}. Rate-limited to 5 attempts per minute per IP. |

### Catalog -- `/api/catalog`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/catalog/pdf` | `product.view` | Generate a printable product catalog as PDF (default), CSV, or HTML. 4-column card grid, 16 products per page. Only in-stock products. Optional comma-separated product IDs, free-text search filters, Query DSL field filters, and visual theme. |

### Sales -- `/api/sales`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/sales` | `sale.view` | Paginated list of sales, newest first. Each sale includes line items and creator username. |
| POST | `/api/sales` | `sale.create` | Create a new sale. Atomic stock decrement via savepoint. Unit price is captured from the product at sale time. created_by tracks the authenticated user. |
| GET | `/api/sales/{sale_id}` | `sale.view` | Return a single sale by ID with all line items and product details. |

### Customers -- `/api/customers`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/customers` | `customer.view` | Return all customers, optionally filtered by name or phone (ILIKE search). |
| POST | `/api/customers` | `customer.create` | Create a new customer record with name, phone, email, and notes. |
| GET | `/api/customers/{customer_id}` | `customer.view` | Return a single customer by ID. |
| PUT | `/api/customers/{customer_id}` | `customer.edit` | Update an existing customer's profile fields. |
| DELETE | `/api/customers/{customer_id}` | `customer.delete` | Delete a customer record. |

### Layaways (apartados) -- `/api/layaways`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/api/layaways` | `apartado.create` | Create a new layaway (apartado). Provide customer_id or inline customer object. Deposit locks in prices and decrements stock. Initial deposit is recorded as the first payment. |
| GET | `/api/layaways` | `apartado.view` | Paginated list of layaways. Filter by status (active/completed/cancelled) and customer_id. |
| GET | `/api/layaways/{layaway_id}` | `apartado.view` | Return a single layaway by ID with items, payments, and customer info. |
| PATCH | `/api/layaways/{layaway_id}` | `apartado.edit` | Update top-level layaway fields (notes) on an active layaway. |
| PATCH | `/api/layaways/{layaway_id}/cancel` | `apartado.edit` | Cancel an active layaway and restore all product stock. |
| PATCH | `/api/layaways/{layaway_id}/complete` | `apartado.edit` | Manually complete an active layaway, creating a linked Sale record. Idempotent if already completed. |
| POST | `/api/layaways/{layaway_id}/items` | `apartado.edit` | Add a new product to an active layaway. Stock is decremented and total/balance recalculated. Price is locked from current product price. |
| DELETE | `/api/layaways/{layaway_id}/items/{item_id}` | `apartado.edit` | Remove an item from an active layaway. Stock is restored and total/balance recalculated. Must keep at least 1 item. |
| PUT | `/api/layaways/{layaway_id}/items/{item_id}` | `apartado.edit` | Change the quantity of an item in an active layaway. Stock is delta-adjusted and total/balance recalculated. |
| POST | `/api/layaways/{layaway_id}/payments` | `apartado.edit` | Add a payment to an active layaway. Amount cannot exceed the outstanding balance. Automatically completes when balance reaches $0. |

### Dashboard -- `/api/dashboard`

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/dashboard` | `dashboard.view` | Aggregated store metrics for a period: sales, daily series, top products, category split, layaways, customers and inventory. Optional start_date/end_date (YYYY-MM-DD, inclusive, at most 365 days); dias sets the default window; top sizes the product rankings; category filters the sales, series, top products and inventory blocks. |


## Query DSL (list endpoints)

All list GET endpoints (`/api/products`, `/api/categories`, `/api/colors`,
`/api/sales`, `/api/customers`, `/api/layaways`) support a shared query DSL on
top of their endpoint-specific parameters.

### Pagination

| Param | Type | Default | Description |
| --- | --- | --- | --- |
| `skip` | int | `0` | Number of records to skip |
| `limit` | int | `100` | Max records to return (1-200) |

`skip`/`limit` take priority over the legacy `page`/`per_page` aliases, which
remain fully supported. Endpoints that previously returned every row
(`/api/categories`, `/api/colors`, `/api/customers`) keep doing so unless
`skip`/`limit` are supplied. `/api/products` with `export=true` ignores
pagination and returns all matches.

### Filter operators

Filters use the field name from the model, with an optional `__op` suffix
(no suffix = `__eq`). Example: `?price__gte=100&name__contains=cuervo`.

| Operator | Description | Example |
| --- | --- | --- |
| `__eq` (default) | Equal | `?status=active` |
| `__ne` | Not equal | `?status__ne=cancelled` |
| `__gt` | Greater than | `?price__gt=100` |
| `__gte` | Greater than or equal | `?stock__gte=10` |
| `__lt` | Less than | `?stock__lt=5` |
| `__lte` | Less than or equal | `?balance__lte=50` |
| `__like` | Case-insensitive LIKE (raw `%` / `_` wildcards) | `?name__like=%%25cuervo%%25` |
| `__contains` | Case-insensitive substring (escaped) | `?name__contains=tequila` |
| `__startswith` | Case-insensitive prefix (escaped) | `?name__startswith=jose` |
| `__endswith` | Case-insensitive suffix (escaped) | `?name__endswith=ml` |
| `__not_like` | NOT LIKE | `?name__not_like=generico` |
| `__in` | In comma-separated list | `?id__in=1,2,3` |
| `__not_in` | Not in comma-separated list | `?id__not_in=4,5,6` |
| `__is_null` | IS NULL / IS NOT NULL (`true`/`false`/`1`/`0`) | `?email__is_null=true` |

Values are coerced to the column type (int, decimal, bool, datetime). Date
columns accept `YYYY-MM-DD` (treated as midnight). String operators
(`__like`, `__contains`, `__startswith`, `__endswith`, `__not_like`) only apply
to text fields. Products additionally accept `category` and `color` as
filter-only fields matched against the related names
(e.g. `?category__contains=herram`). Unknown fields, unknown operators, or
uncoercible values return **400**.

### Field selection

| Param | Description |
| --- | --- |
| `modo` | Preset projection: `basico` (essential fields) or `detallado` (all scalar fields) |
| `campos` | Explicit comma-separated field list, e.g. `campos=id,name,price` |

When `modo` or `campos` is used, list responses contain only the requested
fields (wrapped in the endpoint's usual envelope for products/layaways).
Without them, the standard typed response is returned unchanged. Unknown or
non-selectable fields return **400**.

## Business Rules

### Products

- `code` is globally unique (enforced on create **and** update; error names the conflicting product).
- `name`, `code`, and `price` required; `price >= 0`.
- All referenced `category_ids` / `color_ids` must exist (count validated).
- List endpoint always filters `stock > 0`; stock can still dip to 0 via sell-through.
- Old image file is deleted on image change (update) and on delete.
- Search = case-insensitive ILIKE across code, name, ubicacion, price (`cast` to text), category name, and color name; `%`, `_`, `\` are escaped.

### Sales

- At least one item required: `"La venta debe tener al menos un articulo"`.
- Each product must exist (404) and have sufficient stock (400).
- `unit_price` comes from the product **at sale time**, never from the request; `total` is computed server-side.
- Stock decrement + sale creation wrap in a SQLAlchemy **savepoint** (`db.begin_nested()`): any failure -> no partial sale, no stock change.
- Sales are immutable: no delete/update endpoints.

### Layaways (apartados)

- Exactly one of `customer_id` / inline `customer`.
- `deposit > 0` and `deposit <= total`; initial deposit recorded as first `LayawayPayment`.
- Each item locks the current `unit_price` and **decrements stock** at creation.
- Payments only on `active` layaways; `amount > 0` and `amount <= balance`.
- Payment that brings `balance` to $0 **auto-completes**: creates a linked `Sale` with the locked prices (no second stock decrement).
- Manual `complete` is idempotent (no-op if `sale_id` already set); any remaining positive balance is recorded as a final payment and zeroed.
- Edit notes / add / remove / quantity-change / cancel only on `active` layaways.
- Remove item -> restores stock, must keep >= 1 item.
- Quantity change -> delta stock adjustment (increase decrements, decrease restores).
- Remove/quantity-decrease blocked when the new total would fall below total payments.
- Cancel -> restores all stock, status `cancelled`, payments history retained.

### Image uploads

- Endpoints: `POST /api/upload` (products) and `POST /api/auth/avatar` (profiles).
- Validation by **magic bytes**, not Content-Type/extension.
- Formats: JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), WebP (`52 49 46 46`).
- Max 5 MB, min 8 bytes; random UUID filenames; extension derived from detected type.
- Stored to local `uploads/` or GCS (`GCS_BUCKET`); `safe_upload_path` blocks traversal.

### PDF catalog

- Only in-stock products (`stock > 0`); optional `ids` and `q` filters.
- Ordering: by category product-count (desc), category name, color name, then stock (uncategorized last).
- 4-column x 4-row card grid = **16 products/page** (A4).
- Each card: center-cropped image (40x48 mm @ 72 DPI, JPEG q85) or an initial-letter placeholder, name (truncated to ~2 lines), and a price band with the code.
- Weekly header on every page: `Valido de {lunes} a {domingo} | semana {N}` (Spanish month names, ISO week number, based on today).
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

- `GET /docs` -- this reference as HTML (rendered from this Markdown).
- `GET /redoc` -- ReDoc UI (pinned v2.1.5).
- `GET /api/health` -- `{"status": "ok", "db": "connected"}`; **503** when the database is unreachable (used by Cloud Run probes).

---
*Maintenance: this file is generated from code. Do not edit manually.*
*Regenerate with: `python scripts/generate_api_reference.py` from `backend/`.
