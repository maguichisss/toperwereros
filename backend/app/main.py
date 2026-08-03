"""Store Catalog API — FastAPI application entry point.

Configures logging, CORS, rate limiting, static file serving for uploads,
custom error handlers, and mounts all API routers under ``/api/``.
"""

import json
import logging
import os
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.logging_config import setup_logging
from app.config import UPLOAD_DIR
from app.routers.docs import REDOC_HTML
from app.routers import categories, products, upload, colors, catalog, sales, customers, layaways, auth

setup_logging()
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Store Catalog API",
    redirect_slashes=False,
    docs_url="/swagger",
    redoc_url=None,
    openapi_tags=[
        {"name": "Auth", "description": "Login, JWT tokens, user profile, and user management."},
        {"name": "Products", "description": "Product CRUD with search, pagination, category/color filtering."},
        {"name": "Categories", "description": "Product category management."},
        {"name": "Colors", "description": "Product color management with hex-code validation."},
        {"name": "Upload", "description": "Image upload with magic bytes validation."},
        {"name": "Catalog", "description": "PDF catalog generation for in-stock products."},
        {"name": "Sales", "description": "Sale creation and history with atomic stock decrement."},
        {"name": "Customers", "description": "Customer records with name/phone search."},
        {"name": "Layaways", "description": "Layaway (apartado) lifecycle: create, pay, cancel, complete."},
    ],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle 422 validation errors by logging details and returning a JSON response.

    Args:
        request: The incoming HTTP request that failed validation.
        exc: The validation error containing field-level error details.

    Returns:
        JSONResponse with status 422 and the list of validation errors.
    """

    body = await request.body()
    logger.warning(
        "422 Validation Error on %s %s — body: %s — errors: %s",
        request.method,
        request.url,
        body.decode(),
        exc.errors(),
    )
    errors = json.loads(json.dumps(exc.errors(), default=str))
    return JSONResponse(status_code=422, content={"detail": errors})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(categories.router, prefix="/api/categories")
app.include_router(products.router, prefix="/api/products")
app.include_router(upload.router, prefix="/api/upload")
app.include_router(colors.router, prefix="/api/colors")
app.include_router(catalog.router, prefix="/api/catalog")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(sales.router, prefix="/api/sales")
app.include_router(customers.router, prefix="/api/customers")
app.include_router(layaways.router, prefix="/api/layaways")


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def custom_docs() -> str:
    """Serve the custom HTML documentation page at /docs.

    Returns:
        A self-contained HTML page with endpoint reference, permission
        matrix, and business rules.
    """

    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs.html")
    with open(docs_path, "r") as f:
        return f.read()


@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
def custom_redoc() -> str:
    """Serve the custom ReDoc page at /redoc with a pinned CDN version.

    Returns:
        HTML page that renders the OpenAPI schema via ReDoc @2.1.5.
    """

    return REDOC_HTML
