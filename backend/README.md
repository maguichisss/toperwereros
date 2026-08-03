# Store Catalog API

FastAPI backend for the Toperwereros store catalog — products, sales, layaways (apartados), and PDF catalog generation.

## Tech Stack

- **Framework:** FastAPI 0.115
- **ORM:** SQLAlchemy 2.0 (Mapped style)
- **Database:** PostgreSQL 16
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **PDF:** fpdf2 + Pillow
- **Rate Limiting:** slowapi
- **File Uploads:** python-multipart

## Quick Start (Docker)

```bash
docker compose up -d --build
```

The API will be available at `http://localhost:3001`.

## Local Development

### Prerequisites

- Python 3.13+
- PostgreSQL running locally

### Setup

```bash
cd backend
pip install -r requirements.txt
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/store_catalog` | PostgreSQL connection string |
| `JWT_SECRET` | `dev-secret-change-in-production` | JWT signing secret |
| `JWT_EXPIRE_MINUTES` | `1440` (24h) | Token expiry in minutes |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose output including SQL queries |

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

## API Documentation

| URL | Description |
|-----|-------------|
| [`/docs`](http://localhost:3001/docs) | Custom HTML docs with endpoint reference, permission matrix, and business rules |
| [`/swagger`](http://localhost:3001/swagger) | Swagger UI (interactive) |
| [`/redoc`](http://localhost:3001/redoc) | ReDoc (read-only) |
| [`/openapi.json`](http://localhost:3001/openapi.json) | OpenAPI 3.1 schema |

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | admin |

## Roles

| Role | Access |
|------|--------|
| **admin** | Full access to everything |
| **employee** | Products, sales, layaways, customers, categories (view), colors (view) |
| **viewer** | Read-only access to products, sales, layaways, customers, categories, colors |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # App entry point, CORS, rate limiting, router mounting
│   ├── auth.py               # JWT, password hashing, role/permission system
│   ├── models.py             # SQLAlchemy ORM models (11 models)
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── database.py           # Engine, session factory, get_db dependency
│   ├── config.py             # Shared constants, upload helpers, LIKE escaping
│   ├── logging_config.py     # Centralized logging setup
│   └── routers/
│       ├── auth.py           # Login, profile, user management (9 endpoints)
│       ├── products.py       # Product CRUD + search (5 endpoints)
│       ├── categories.py     # Category CRUD (4 endpoints)
│       ├── colors.py         # Color CRUD (4 endpoints)
│       ├── upload.py         # Image upload (1 endpoint)
│       ├── catalog.py        # PDF catalog generation (1 endpoint)
│       ├── sales.py          # Sale creation + listing (3 endpoints)
│       ├── customers.py      # Customer CRUD (5 endpoints)
│       ├── layaways.py       # Layaway lifecycle + item management (9 endpoints)
│       └── docs.py           # Custom HTML documentation page
├── docs.html                 # HTML documentation (served at /api/docs)
├── requirements.txt
├── Dockerfile
└── docker-entrypoint.sh
```
