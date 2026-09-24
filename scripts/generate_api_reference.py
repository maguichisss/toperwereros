#!/usr/bin/env python3
"""
Generate docs/api-reference.md from FastAPI app's OpenAPI schema.

Single source of truth: the code. This script introspects:
  - app.openapi() for endpoint schema (paths, methods, params, responses)
  - app.routes for dependency-permission mapping
  - app.auth.ROLE_PERMISSIONS for the permission matrix

Usage:
    python scripts/generate_api_reference.py                 # writes docs/api-reference.md
    python scripts/generate_api_reference.py --check         # exit 1 if drift detected
    python scripts/generate_api_reference.py --output /tmp/out.md  # custom output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Boot strap: ensure we can import app
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Imports after path fix
from app.main import app  # noqa: E402
from app.auth import ROLE_PERMISSIONS  # noqa: E402

# Import shared permission utilities
from scripts.permission_utils import (
    extract_permissions_from_route,
    get_route_permission_classification,
    analyze_route_permission_coverage,
    format_coverage_report,
    PUBLIC_ROUTES,
    AUTH_ONLY_ALLOWLIST,
)

# Constants
DOCS_DIR = REPO_ROOT / "docs"
API_REF_PATH = DOCS_DIR / "api-reference.md"
ROLES_MARKER_START = "<!-- ROLES:START -->"
ROLES_MARKER_END = "<!-- ROLES:END -->"
API_META_MARKER = "<!-- API-META:"

# Permission extraction from dependencies - using shared utilities
def get_route_permission(route: Any) -> str:
    """Return permission string, or 'public' / 'authenticated' fallbacks."""
    perms = extract_permissions_from_route(route)
    if perms:
        return sorted(perms)[0]  # Return first for display
    if hasattr(route, "dependencies") and route.dependencies:
        for dep in route.dependencies:
            callable_obj = getattr(dep, "dependency", None) or getattr(dep, "call", None)
            if callable_obj and hasattr(callable_obj, "__name__"):
                if "get_current_user" in callable_obj.__name__:
                    return "authenticated"
    return "public"


def collect_routes() -> List[Dict[str, Any]]:
    """
    Walk app.routes and extract a structured list of endpoints with
    permission, method, path, summary, description.
    """
    routes = []
    seen = set()
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        if route.path in ("/docs", "/redoc", "/openapi.json", "/api/health"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            key = (method, route.path)
            if key in seen:
                continue
            seen.add(key)
            routes.append({
                "method": method,
                "path": route.path,
                "summary": getattr(route, "summary", "") or "",
                "description": getattr(route, "description", "") or "",
                "permission": get_route_permission(route),
            })
    tag_order = {
        "/api/auth": 0,
        "/api/products": 1,
        "/api/categories": 2,
        "/api/colors": 3,
        "/api/upload": 4,
        "/api/catalog": 5,
        "/api/sales": 6,
        "/api/customers": 7,
        "/api/layaways": 8,
    }
    def sort_key(r):
        prefix = next((p for p in tag_order if r["path"].startswith(p)), "zzz")
        return (tag_order.get(prefix, 99), r["path"])
    routes.sort(key=sort_key)
    return routes


def group_by_tag(routes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group routes by their module tag (Auth, Products, etc.)."""
    groups = {}
    for r in routes:
        if r["path"].startswith("/api/auth"):
            tag = "Auth"
        elif r["path"].startswith("/api/products"):
            tag = "Products"
        elif r["path"].startswith("/api/categories"):
            tag = "Categories"
        elif r["path"].startswith("/api/colors"):
            tag = "Colors"
        elif r["path"].startswith("/api/upload"):
            tag = "Upload"
        elif r["path"].startswith("/api/catalog"):
            tag = "Catalog"
        elif r["path"].startswith("/api/sales"):
            tag = "Sales"
        elif r["path"].startswith("/api/customers"):
            tag = "Customers"
        elif r["path"].startswith("/api/layaways"):
            tag = "Layaways"
        else:
            tag = "Other"
        groups.setdefault(tag, []).append(r)
    tag_order = ["Auth", "Products", "Categories", "Colors", "Upload",
                 "Catalog", "Sales", "Customers", "Layaways", "Other"]
    return {tag: groups[tag] for tag in tag_order if tag in groups}


def render_permission_matrix(perms: Dict[str, List[str]]) -> str:
    """Render the JSON block for the permission matrix (machine-readable)."""
    return f"{ROLES_MARKER_START}\n```json\n{json.dumps(perms, separators=(',', ':'))}\n```\n{ROLES_MARKER_END}"


def render_permission_table(perms: Dict[str, List[str]]) -> str:
    """Render the human-readable permission matrix table (ATOMIC ONLY - no composites)."""
    all_perms = sorted({p for role_perms in perms.values() for p in role_perms if p != "*"})
    lines = ["| Permission | admin | employee | viewer |", "| --- | :-: | :-: | :-: |"]
    for perm in all_perms:
        admin = "✓" if "*" in perms.get("admin", []) or perm in perms.get("admin", []) else ""
        employee = "✓" if perm in perms.get("employee", []) else ""
        viewer = "✓" if perm in perms.get("viewer", []) else ""
        lines.append(f"| `{perm}` | {admin} | {employee} | {viewer} |")
    return "\n".join(lines)


def render_endpoint_table(routes: List[Dict[str, Any]]) -> str:
    """Render a markdown table for a group of endpoints."""
    lines = ["| Method | Path | Permission | Description |", "| --- | --- | --- | --- |"]
    for r in routes:
        perm = r["permission"]
        if perm == "public":
            perm_display = "public"
        elif perm == "authenticated":
            perm_display = "authenticated"
        else:
            perm_display = f"`{perm}`"
        desc = (r["description"] or r["summary"] or "").replace("|", "\\|")
        lines.append(f"| {r['method']} | `{r['path']}` | {perm_display} | {desc} |")
    return "\n".join(lines)


def render_api_meta(routes: List[Dict[str, Any]]) -> str:
    """Generate the API-META comment block with stats."""
    endpoint_count = len(routes)
    module_count = len(group_by_tag(routes))
    role_count = len(ROLE_PERMISSIONS)
    permission_count = sum(len(v) for v in ROLE_PERMISSIONS.values() if "*" not in v)
    meta = {
        "endpoints": endpoint_count,
        "modules": module_count,
        "roles": role_count,
        "permissions": permission_count,
    }
    return f"<!-- API-META: {json.dumps(meta)} -->"


def render_coverage_appendix() -> str:
    """Render the route-permission coverage report (computed from live code)."""
    analysis = analyze_route_permission_coverage(list(app.routes), ROLE_PERMISSIONS)
    report = format_coverage_report(analysis)
    return (
        "### Permission inventory & coverage\n\n"
        "Computed from the live routes and `ROLE_PERMISSIONS`; enforced by\n"
        "[`test_route_permissions.py`](../backend/tests/test_route_permissions.py).\n\n"
        "```text\n"
        f"{report}\n"
        "```"
    )


def render_static_sections() -> str:
    """Return the static sections (Query DSL, Business Rules, Env, etc.) as-is."""
    return (
        "\n"
        "## Query DSL (list endpoints)\n\n"
        "All list GET endpoints (`/api/products`, `/api/categories`, `/api/colors`,\n"
        "`/api/sales`, `/api/customers`, `/api/layaways`) support a shared query DSL on\n"
        "top of their endpoint-specific parameters.\n\n"
        "### Pagination\n\n"
        "| Param | Type | Default | Description |\n"
        "| --- | --- | --- | --- |\n"
        "| `skip` | int | `0` | Number of records to skip |\n"
        "| `limit` | int | `100` | Max records to return (1-200) |\n\n"
        "`skip`/`limit` take priority over the legacy `page`/`per_page` aliases, which\n"
        "remain fully supported. Endpoints that previously returned every row\n"
        "(`/api/categories`, `/api/colors`, `/api/customers`) keep doing so unless\n"
        "`skip`/`limit` are supplied. `/api/products` with `export=true` ignores\n"
        "pagination and returns all matches.\n\n"
        "### Filter operators\n\n"
        "Filters use the field name from the model, with an optional `__op` suffix\n"
        "(no suffix = `__eq`). Example: `?price__gte=100&name__contains=cuervo`.\n\n"
        "| Operator | Description | Example |\n"
        "| --- | --- | --- |\n"
        "| `__eq` (default) | Equal | `?status=active` |\n"
        "| `__ne` | Not equal | `?status__ne=cancelled` |\n"
        "| `__gt` | Greater than | `?price__gt=100` |\n"
        "| `__gte` | Greater than or equal | `?stock__gte=10` |\n"
        "| `__lt` | Less than | `?stock__lt=5` |\n"
        "| `__lte` | Less than or equal | `?balance__lte=50` |\n"
        "| `__like` | Case-insensitive LIKE (raw `%` / `_` wildcards) | `?name__like=%%25cuervo%%25` |\n"
        "| `__contains` | Case-insensitive substring (escaped) | `?name__contains=tequila` |\n"
        "| `__startswith` | Case-insensitive prefix (escaped) | `?name__startswith=jose` |\n"
        "| `__endswith` | Case-insensitive suffix (escaped) | `?name__endswith=ml` |\n"
        "| `__not_like` | NOT LIKE | `?name__not_like=generico` |\n"
        "| `__in` | In comma-separated list | `?id__in=1,2,3` |\n"
        "| `__not_in` | Not in comma-separated list | `?id__not_in=4,5,6` |\n"
        "| `__is_null` | IS NULL / IS NOT NULL (`true`/`false`/`1`/`0`) | `?email__is_null=true` |\n\n"
        "Values are coerced to the column type (int, decimal, bool, datetime). Date\n"
        "columns accept `YYYY-MM-DD` (treated as midnight). String operators\n"
        "(`__like`, `__contains`, `__startswith`, `__endswith`, `__not_like`) only apply\n"
        "to text fields. Products additionally accept `category` and `color` as\n"
        "filter-only fields matched against the related names\n"
        "(e.g. `?category__contains=herram`). Unknown fields, unknown operators, or\n"
        "uncoercible values return **400**.\n\n"
        "### Field selection\n\n"
        "| Param | Description |\n"
        "| --- | --- |\n"
        "| `modo` | Preset projection: `basico` (essential fields) or `detallado` (all scalar fields) |\n"
        "| `campos` | Explicit comma-separated field list, e.g. `campos=id,name,price` |\n\n"
        "When `modo` or `campos` is used, list responses contain only the requested\n"
        "fields (wrapped in the endpoint's usual envelope for products/layaways).\n"
        "Without them, the standard typed response is returned unchanged. Unknown or\n"
        "non-selectable fields return **400**.\n\n"
        "## Business Rules\n\n"
        "### Products\n\n"
        "- `code` is globally unique (enforced on create **and** update; error names the conflicting product).\n"
        "- `name`, `code`, and `price` required; `price >= 0`.\n"
        "- All referenced `category_ids` / `color_ids` must exist (count validated).\n"
        "- List endpoint always filters `stock > 0`; stock can still dip to 0 via sell-through.\n"
        "- Old image file is deleted on image change (update) and on delete.\n"
        "- Search = case-insensitive ILIKE across code, name, ubicacion, price (`cast` to text), category name, and color name; `%`, `_`, `\\` are escaped.\n\n"
        "### Sales\n\n"
        "- At least one item required: `\"La venta debe tener al menos un articulo\"`.\n"
        "- Each product must exist (404) and have sufficient stock (400).\n"
        "- `unit_price` comes from the product **at sale time**, never from the request; `total` is computed server-side.\n"
        "- Stock decrement + sale creation wrap in a SQLAlchemy **savepoint** (`db.begin_nested()`): any failure -> no partial sale, no stock change.\n"
        "- Sales are immutable: no delete/update endpoints.\n\n"
        "### Layaways (apartados)\n\n"
        "- Exactly one of `customer_id` / inline `customer`.\n"
        "- `deposit > 0` and `deposit <= total`; initial deposit recorded as first `LayawayPayment`.\n"
        "- Each item locks the current `unit_price` and **decrements stock** at creation.\n"
        "- Payments only on `active` layaways; `amount > 0` and `amount <= balance`.\n"
        "- Payment that brings `balance` to $0 **auto-completes**: creates a linked `Sale` with the locked prices (no second stock decrement).\n"
        "- Manual `complete` is idempotent (no-op if `sale_id` already set); any remaining positive balance is recorded as a final payment and zeroed.\n"
        "- Edit notes / add / remove / quantity-change / cancel only on `active` layaways.\n"
        "- Remove item -> restores stock, must keep >= 1 item.\n"
        "- Quantity change -> delta stock adjustment (increase decrements, decrease restores).\n"
        "- Remove/quantity-decrease blocked when the new total would fall below total payments.\n"
        "- Cancel -> restores all stock, status `cancelled`, payments history retained.\n\n"
        "### Image uploads\n\n"
        "- Endpoints: `POST /api/upload` (products) and `POST /api/auth/avatar` (profiles).\n"
        "- Validation by **magic bytes**, not Content-Type/extension.\n"
        "- Formats: JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), WebP (`52 49 46 46`).\n"
        "- Max 5 MB, min 8 bytes; random UUID filenames; extension derived from detected type.\n"
        "- Stored to local `uploads/` or GCS (`GCS_BUCKET`); `safe_upload_path` blocks traversal.\n\n"
        "### PDF catalog\n\n"
        "- Only in-stock products (`stock > 0`); optional `ids` and `q` filters.\n"
        "- Ordering: by category product-count (desc), category name, color name, then stock (uncategorized last).\n"
        "- 4-column x 4-row card grid = **16 products/page** (A4).\n"
        "- Each card: center-cropped image (40x48 mm @ 72 DPI, JPEG q85) or an initial-letter placeholder, name (truncated to ~2 lines), and a price band with the code.\n"
        "- Weekly header on every page: `Valido de {lunes} a {domingo} | semana {N}` (Spanish month names, ISO week number, based on today).\n"
        "- Themes: `classic`, `nocturno`, `kraft`, `elegante`, `marino`, `sol`, `cyber`, `vino`, `rosa`, `arcoiris`, `nebulosa`, `triangulos`, `olas`, `mandala`, `aurora`, `confeti`, `galaxia`, `marco`, `flores`.\n"
        "- Output: PDF (attachment) or HTML (inline); `format`/`theme`/`ids` validation errors are 400.\n"
        "- Layout mirrors [`docs/card-mockup.html`](card-mockup.html).\n\n"
        "## Environment Variables\n\n"
        "| Variable | Default | Description |\n"
        "| --- | --- | --- |\n"
        "| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/store_catalog` | SQLAlchemy connection string |\n"
        "| `JWT_SECRET` | *(required)* | HS256 signing key (sample in `.env.example`) |\n"
        "| `JWT_EXPIRE_MINUTES` | `1440` | Access-token lifetime (minutes) |\n"
        "| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh-token lifetime (days) |\n"
        "| `LOCKOUT_MAX_ATTEMPTS` | `5` | Failed logins before lockout |\n"
        "| `LOCKOUT_DURATION_MINUTES` | `15` | Lockout window |\n"
        "| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |\n"
        "| `LOG_LEVEL` | `INFO` | Python logging level |\n"
        "| `DEFAULT_ADMIN_PASSWORD` | `admin123` | Seed password for default admin ([`seed.py`](../backend/seed.py)) |\n"
        "| `GCS_BUCKET` | *(empty)* | Set to store uploads in Google Cloud Storage |\n"
        "| `GCP_PROJECT` | *(empty)* | GCP project id (GCS / Cloud SQL only) |\n"
        "| `CLOUD_SQL_CONNECTION_STRING` | *(empty)* | Starts the embedded Cloud SQL Auth Proxy |\n\n"
        "Full deployment context: [`docs/technical/deployment.md`](technical/deployment.md).\n\n"
        "## Rate Limits\n\n"
        "Applied via slowapi, keyed per authenticated user (`user:{id}`) or client IP:\n\n"
        "| Endpoint | Limit |\n"
        "| --- | --- |\n"
        "| `POST /api/auth/login` | 5 / minute |\n"
        "| `POST /api/auth/refresh` | 10 / minute |\n"
        "| `POST /api/auth/change-password` | 1 / minute |\n"
        "| `POST /api/auth/avatar` | 3 / minute |\n"
        "| `POST /api/auth/register` | 5 / minute |\n"
        "| `POST /api/upload` | 5 / minute |\n\n"
        "Exceeding a limit returns `429 Too Many Requests`.\n\n"
        "## Error Responses\n\n"
        "All errors return JSON with a `detail` field (array for 422).\n\n"
        "| Status | Meaning |\n"
        "| --- | --- |\n"
        "| `400` | Validation error (bad input, duplicate code, insufficient stock, etc.) |\n"
        "| `401` | Not authenticated / invalid or expired token |\n"
        "| `403` | Authenticated but lacking the required permission |\n"
        "| `404` | Resource not found |\n"
        "| `409` | Conflict (duplicate name, category/color in use) |\n"
        "| `422` | Request validation (malformed body) |\n"
        "| `429` | Rate limit exceeded |\n"
        "| `500` | Internal server error |\n\n"
        "## Service endpoints (not in OpenAPI)\n\n"
        "- `GET /docs` -- this reference as HTML (rendered from this Markdown).\n"
        "- `GET /redoc` -- ReDoc UI (pinned v2.1.5).\n"
        "- `GET /api/health` -- `{\"status\": \"ok\", \"db\": \"connected\"}`; **503** when the database is unreachable (used by Cloud Run probes).\n\n"
        "---\n"
        "*Maintenance: this file is generated from code. Do not edit manually.*\n"
        "*Regenerate with: `python scripts/generate_api_reference.py` from `backend/`.\n"
    )


def build_markdown() -> str:
    """Assemble the complete api-reference.md content."""
    routes = collect_routes()
    groups = group_by_tag(routes)

    parts = [
        "# Store Catalog API Reference",
        "",
        "> This document is the **single source of truth** for the public API contract.",
        "> It is rendered into [`backend/docs.html`](../backend/docs.html) by [`scripts/generate_docs_html.py`](../scripts/generate_docs_html.py)",
        "> and served at `/docs`. Two pytest guards ([`test_docs_permissions.py`](../backend/tests/test_docs_permissions.py),",
        "> [`test_docs_generated.py`](../backend/tests/test_docs_generated.py)) keep it in sync with the code.",
        "> Interactive schemas: `/swagger` (OpenAPI) · `/redoc` · `/openapi.json`.",
        "",
        "## Overview",
        "",
        "FastAPI backend for Toperwereros: authentication (JWT), product catalog,",
        "categories, colors, image upload, PDF catalog generation, sales (POS),",
        "customers, and layaways (apartados). Every endpoint except `POST /api/auth/login`",
        "requires a JWT Bearer token. Response/error messages are in Spanish.",
        "",
        render_api_meta(routes),
        "",
        "## Authentication",
        "",
        "All endpoints except `POST /api/auth/login` require:",
        "",
        "```",
        "Authorization: Bearer <access_token>",
        "```",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        "| Token format | JWT, algorithm HS256 |",
        "| Access-token expiry | `JWT_EXPIRE_MINUTES` (default `1440` = 24 h) |",
        "| Refresh-token expiry | `REFRESH_TOKEN_EXPIRE_DAYS` (default `7`) |",
        "| Secret | `JWT_SECRET` env var (**required** at startup; sample in `.env.example`) |",
        "| Password hashing | bcrypt (`passlib`) |",
        "| Login lockout | 5 failed attempts -> locked for `LOCKOUT_DURATION_MINUTES` (15) |",
        "",
        "Refresh tokens are opaque, stored by SHA-256 hash with family tracking\n"
        "(rotation + family revoke on reuse). `POST /api/auth/refresh` exchanges a valid\n"
        "refresh token for a new access+refresh pair (the old one is revoked).",
        "",
        "## Roles & Permissions",
        "",
        "| Role | Level | Capabilities |",
        "| --- | --- | --- |",
        "| `admin` | `*` (wildcard) | Full access to all endpoints, including user/role management |",
        "| `employee` | 15 permissions | Products (CRUD), sales (view/create), layaways (view/create/edit), customers (CRUD), categories (view), colors (view) |",
        "| `viewer` | 6 permissions | Read-only: products, sales, layaways, customers, categories, colors |",
        "",
        "### Permission matrix (machine-readable source)",
        "",
        "This block is authoritative for the permission drift test -- it must equal\n"
        "`app.auth.ROLE_PERMISSIONS`.",
        "",
        render_permission_matrix(ROLE_PERMISSIONS),
        "",
        "### Permission matrix (human-readable)",
        "",
        render_permission_table(ROLE_PERMISSIONS),
        "",
        "Admin bypasses all checks via the `*` wildcard; permission strings may also be\n"
        "matched by a `.*` parent (e.g. a role holding `product.*` satisfies\n"
        "`product.view`).",
        "",
        render_coverage_appendix(),
        "",
        "## Endpoint Reference",
        "",
    ]

    section_order = [
        "Auth", "Products", "Categories", "Colors", "Upload",
        "Catalog", "Sales", "Customers", "Layaways",
    ]
    for tag in section_order:
        if tag not in groups:
            continue
        tag_routes = groups[tag]
        tag_display = {
            "Auth": "Auth -- `/api/auth`",
            "Products": "Products -- `/api/products`",
            "Categories": "Categories -- `/api/categories`",
            "Colors": "Colors -- `/api/colors`",
            "Upload": "Upload -- `/api/upload`",
            "Catalog": "Catalog -- `/api/catalog`",
            "Sales": "Sales -- `/api/sales`",
            "Customers": "Customers -- `/api/customers`",
            "Layaways": "Layaways (apartados) -- `/api/layaways`",
        }.get(tag, tag)
        parts.append(f"### {tag_display}")
        parts.append("")
        parts.append(render_endpoint_table(groups[tag]))
        parts.append("")

    parts.append(render_static_sections())

    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/api-reference.md from FastAPI OpenAPI schema."
    )
    parser.add_argument(
        "--output", default=str(API_REF_PATH), help="Output markdown path (use - for stdout)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Exit 1 if generated content differs from committed file"
    )
    args = parser.parse_args()

    generated = build_markdown()

    if args.check:
        try:
            current = API_REF_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"ERROR: {API_REF_PATH} does not exist", file=sys.stderr)
            return 1
        if current != generated:
            print("DRIFT DETECTED: api-reference.md is out of sync with code.", file=sys.stderr)
            return 1
        print("OK: api-reference.md is in sync with code.", file=sys.stderr)
        return 0

    out_path = args.output
    if out_path == "-":
        sys.stdout.write(generated)
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(generated, encoding="utf-8")
    print(f"Generated {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())