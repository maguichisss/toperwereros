# Overview

Store Catalog is the product-management system for **Toperwereros**. It is a
full-stack web application for running a physical store:

- a browsable **product catalog** with photos, categories and colors,
- **POS-style sales** with atomic stock decrements,
- **layaway plans** ("apartados") with deposits and installment payments,
- printable weekly **PDF catalogs** for distribution,
- role-based accounts (admin / employee / viewer).

## Stack

| Layer | Technology | Notes |
| --- | --- | --- |
| Frontend | React 18 (Vite), plain CSS | Single page, tab-based UI; served by nginx |
| API | FastAPI (Python 3.11) | REST, Pydantic v2 schemas, OpenAPI at `/api/docs` |
| ORM / DB | SQLAlchemy 2.0 / PostgreSQL | 11 tables; migrations via Alembic |
| Auth | JWT (HS256) + opaque refresh tokens | bcrypt password hashing, role-based permissions |
| Catalog output | fpdf2 + Pillow | PDF or HTML, 4-column card grid, 16 products/page |
| Uploads | Local disk or Google Cloud Storage | env-selected via `GCS_BUCKET` |

## Runtime shape

In every deployment the frontend is served as static files that call the
backend through an `/api` prefix (and `/uploads` for images). During local dev
Vite proxies those prefixes to the FastAPI server; in production nginx does
the same job.

## Key behaviors to know up front

1. **Sales are stock-atomic.** Creating a sale validates and decrements stock
   inside a savepoint; on any failure nothing is persisted.
2. **Layaways can auto-complete into a sale.** When a layaway's balance reaches
   zero it is finalized against a linked `Sale`, debiting the reserved stock.
3. **The PDF catalog shows in-stock products only**, ordered newest-first for
   the first 64 products and by category/color/stock afterwards.
4. **Auth is JWT-based with refresh-token rotation.** Every role maps to a
   permission set defined in [`backend/app/auth.py`](../../backend/app/auth.py); behavioral summaries live
   in [Docs: business (ES)](../business/index.md).

## Documentation map

| Doc | Audience |
| --- | --- |
| [Architecture](architecture.md) | Developers |
| [Deployment](deployment.md) | Operators / DevOps |
| [Database](database.md) | Developers / operators |
| [Auth & security](auth-security.md) | Developers / operators |
| [Testing](testing.md) | Developers |
| [API reference](../api-reference.md) | Developers |
| [Business rules (ES)](../business/index.md) | Owners / operators |
| [User guides (ES)](../user-guides/index.md) | End users |
| [Flows (ES)](../flows/index.md) | Everyone |