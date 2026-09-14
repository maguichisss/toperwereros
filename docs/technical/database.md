# Database

PostgreSQL, accessed through SQLAlchemy 2.0 ORM. The canonical schema is
[`backend/app/models.py`](../../backend/app/models.py) — 11 tables plus two many-to-many association tables.

```mermaid
erDiagram
    colors ||--o{ product_colors : "in"
    products ||--o{ product_colors : "has"
    categories ||--o{ product_categories : "in"
    products ||--o{ product_categories : "has"

    roles ||--o{ users : "assigns"
    users ||--o{ refresh_tokens : "owns"
    users ||--o{ sales : "created"
    users ||--o{ layaways : "created"

    products ||--o{ sale_items : "sold in"
    sales ||--o{ sale_items : "contains"

    customers ||--o{ layaways : "has"
    layaways ||--o{ layaway_items : "contains"
    layaways ||--o{ layaway_payments : "payment history"
    sales ||--o| layaways : "liquidation (nullable)"

    products ||--o{ layaway_items : "reserved in"

    colors {
        int id PK
        string name UK "unique"
        string hex "String(7) #RRGGBB"
        datetime created_at "server default now()"
    }
    categories {
        int id PK
        string name UK "unique"
        datetime created_at
        datetime updated_at "onupdate"
    }
    products {
        int id PK
        string name
        string code
        int stock "default 1"
        string description "nullable"
        string ubicacion "nullable"
        numeric price "Numeric(10,2)"
        string image_url "nullable"
        datetime created_at
        datetime updated_at "onupdate"
    }
    product_colors {
        int product_id FK "PK, cascade"
        int color_id FK "PK, cascade"
    }
    product_categories {
        int product_id FK "PK, cascade"
        int category_id FK "PK, cascade"
    }
    roles {
        int id PK
        string name UK "unique"
    }
    users {
        int id PK
        string username UK
        string email UK "nullable"
        string hashed_password "bcrypt"
        boolean active "default true"
        int role_id FK
        string image_url "nullable"
        int failed_login_attempts "default 0"
        datetime locked_until "nullable"
        datetime created_at
        datetime updated_at "onupdate"
    }
    refresh_tokens {
        int id PK
        string token_hash UK "sha256, indexed"
        int user_id FK "cascade"
        string family_id "indexed"
        datetime expires_at
        boolean revoked "default false"
        datetime created_at
    }
    sales {
        int id PK
        numeric total "Numeric(10,2)"
        int created_by FK "nullable"
        datetime created_at
    }
    sale_items {
        int id PK
        int sale_id FK "cascade"
        int product_id FK
        int quantity "default 1"
        numeric unit_price "Numeric(10,2), price at sale time"
    }
    customers {
        int id PK
        string name
        string phone "nullable"
        string email "nullable"
        string notes "nullable"
        datetime created_at
        datetime updated_at "onupdate"
    }
    layaways {
        int id PK
        int customer_id FK
        numeric total "Numeric(10,2)"
        numeric deposit "Numeric(10,2)"
        numeric balance "Numeric(10,2)"
        string status "active | completed | cancelled"
        int sale_id FK "nullable, liquidation"
        int created_by FK "nullable"
        string notes "nullable"
        datetime created_at
        datetime updated_at "onupdate"
    }
    layaway_items {
        int id PK
        int layaway_id FK "cascade"
        int product_id FK
        int quantity
        numeric unit_price "locked-in price, Numeric(10,2)"
    }
    layaway_payments {
        int id PK
        int layaway_id FK "cascade"
        numeric amount "Numeric(10,2)"
        datetime created_at
    }
```

## Schema conventions

- **Monetary and quantity fields** are `Numeric(10, 2)`; totals are computed
  server-side, never trusted from the client.
- **Timestamps**: `created_at = server_default=func.now()`;
  `updated_at` additionally has `onupdate=func.now()`. Both are `nullable` in
  the ORM so server defaults apply at insert.
- **Cascades**:
  - `product_colors` / `product_categories` rows cascade on product delete
    (also on color/category delete via the other FK).
  - `sale_items`, `layaway_items`, and `layaway_payments` delete with their
    parent row (`ondelete="CASCADE"` client-side).
  - `refresh_tokens` cascade when a user is deleted.
  - `users.created_by` / `layaways.created_by` / `sales.created_by` → `users`
    are soft (nullable, no cascade): deleting a user is expected to be
    blocked/absent rather than removing history.
  - `layaways.sale_id` is nullable and set only when a layaway is liquidated
    into a sale.

## Uniqueness rules

- `colors.name`, `categories.name`, `roles.name`, `users.username`
  (and `users.email` when present) are unique.
- `refresh_tokens.token_hash` is unique.

## Status domain

`layaways.status` takes one of `active`, `completed`, `cancelled`. There is no
CHECK constraint in the ORM; the router ([`app/routers/layaways.py`](../../backend/app/routers/layaways.py)) is the
enforcement point. `products.stock` is a plain integer; the business rule
"stock must never go negative" is enforced at write time in the sale/layaway
routers, not by a DB constraint.

## Schema management

- `docker-entrypoint.sh` runs `Base.metadata.create_all` to ensure tables, then
  `alembic upgrade head` when migration history exists, otherwise
  `alembic stamp head` (fresh DB bootstrapped from models).
- The dev `db` service is `postgres:16-alpine`; Cloud SQL runs PostgreSQL 16.

## Concurrency note

Single-process deployments (gunicorn, 2 workers) rely on the *savepoint-per-
transaction* pattern (see [`sales.py`](../../backend/app/routers/sales.py), [`layaways.py`](../../backend/app/routers/layaways.py)) for stock decrements; the
read-modify-write on `products.stock` is not `SELECT … FOR UPDATE` guarded
today — a known limitation if horizontal scaling is ever introduced.