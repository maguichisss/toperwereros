# Authentication & Security

All authn/authz lives in [`backend/app/auth.py`](../../backend/app/auth.py) (primitives + guards) and
[`backend/app/routers/auth.py`](../../backend/app/routers/auth.py) (endpoints). [`backend/app/config.py`](../../backend/app/config.py) holds the
relevant constants.

## Authentication flow

1. `POST /api/auth/login` — checks username, `active` flag, `locked_until`,
   bcrypt password; on success resets the failure counter and issues an
   **access JWT** plus an **opaque refresh token**.
2. Requests send `Authorization: Bearer <access_token>`.
3. `get_current_user` dependency decodes the JWT (`sub` = user id), looks up the
   user, and rejects (401) if missing or `active = False`.
4. When the access token expires, the SPA calls `POST /api/auth/refresh` and
   retries the request (single-flight in [`client.js`](../../frontend/src/api/client.js)).

## Access tokens (JWT)

- Algorithm `HS256`, signed with `JWT_SECRET` (required at import — the app
  refuses to boot without it).
- Lifetime: `JWT_EXPIRE_MINUTES` (default **1440** = 24 h).
- Contains `sub` (user id, coerced to `str`) and `exp`.

## Refresh tokens (opaque, rotating)

- `secrets.token_urlsafe(32)`; only the **SHA-256 hash** is stored
  (`refresh_tokens.token_hash`), so a DB leak doesn't expose usable tokens.
- Lifetime: `REFRESH_TOKEN_EXPIRE_DAYS` (default **7**).
- **Rotation**: every `/auth/refresh` marks the used token `revoked` and issues
  a new pair in the same `family_id`.
- **Family revoke**: reusing a revoked token revokes the *entire family* —
  this detects token theft/replay.
- **Logout / password change** revoke all of the user's refresh tokens.

## Brute-force protection

| Control | Default | Scope |
| --- | --- | --- |
| `LOCKOUT_MAX_ATTEMPTS` | 5 | consecutive failed logins |
| `LOCKOUT_DURATION_MINUTES` | 15 | lockout window after exceeding attempts |
| `/api/auth/login` rate limit | 5/min/IP | slowapi |
| `/api/auth/refresh` rate limit | 10/min/IP | slowapi |
| `/api/auth/change-password` | 1/min/IP | slowapi |
| `/api/auth/avatar` upload | 3/min/IP | slowapi |
| `/api/auth/register` | 5/min/IP | slowapi |

Rate-limit keys come from `get_rate_limit_key`: a JWT-authenticated user is
bucketed per `user:{id}`, anonymous requests per client IP (via
`X-Forwarded-For` when behind a proxy).

## Authorization — `ROLE_PERMISSIONS`

The role → permission matrix is the source of truth. Admin holds the wildcard
`*`; every other permission string may also be matched by `.*` (e.g. a role
holding `product.*` is granted `product.view`).

| Role | Permissions |
| --- | --- |
| `admin` | `*` |
| `employee` | `product.view/create/edit/delete`, `sale.view/create`, `apartado.view/create/edit`, `customer.view/create/edit/delete`, `category.view`, `color.view` |
| `viewer` | `product.view`, `sale.view`, `apartado.view`, `customer.view`, `category.view`, `color.view` |

`require_permission(*perms)` is a FastAPI dependency: it 403s when the user
lacks at least one of the requested permissions (or a `*` parent). The SPA
mirrors this in `AuthContext.can()` to hide actions, but the backend always
re-checks.

Admin user-management endpoints (`/auth/users`, `/auth/roles`, `/auth/register`)
require `user.manage`, granted only to `admin` via the wildcard.

## Admin-safety guards (routers/auth.py)

- You cannot **deactivate yourself**.
- You cannot **change your own role**.
- Username and email must be unique across users (checked, then enforced by DB
  unique constraints).

## Account lifecycle rules

- Login normalizes the username to **lowercase** before lookup.
- Failed login increments `failed_login_attempts`; reaching the max sets
  `locked_until`; a success resets both.
- A locked account returns the same generic 401 (`"Usuario o contraseña
  incorrectos"`) — login responses don't leak account state.

## Uploads security

- **Magic-byte validation** ([`app/config.py::detect_image_type`](../../backend/app/config.py)): only JPEG,
  PNG, WebP are accepted — never the file extension.
- **Size cap** `MAX_SIZE = 5 MB`, enforced while streaming.
- **Path traversal guard** `safe_upload_path()`: resolved paths must stay under
  `UPLOAD_DIR` (used for local reads/`/uploads`).
- Uploaded filenames are random UUIDs (`avatar_<hex>` / `<uuid>.<ext>`).
- Avatars replace the previous file (local delete or GCS delete) on re-upload.

## CORS

`CORS_ORIGINS` (comma-separated; `*` in dev) controls allowed origins. Cloud
Run deploys set it to the frontend URL (see [deployment.md](deployment.md)).

## Deployment security checklist

- Set a strong random `JWT_SECRET` (never the sample value) and store it in
  Secret Manager on GCP.
- Rotate `DEFAULT_ADMIN_PASSWORD` from the seed default.
- HTTPS everywhere: Pi uses mkcert-terminated TLS; Cloud Run is TLS by default.
- Backend Cloud Run service is `--no-allow-unauthenticated` (frontend only is
  public).
- Never commit `.env*` files (gitignored).

## Known limitations

- Access tokens live in `localStorage` (XSS-readable); the app ships no
  third-party runtime scripts, which mitigates the most common exfiltration.
- No CSRF tokens — the API relies on the `Authorization` header (unaffected by
  CSRF) rather than cookies.
- Rate limiting is enforced per-IP (and per-user where a token exists), not
  per-account for anonymous login attempts.