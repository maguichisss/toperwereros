import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import categories, products, upload, colors, catalog, sales, customers, layaways, auth

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Store Catalog API", redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    print(f"422 Validation Error on {request.method} {request.url}")
    print(f"  Body: {body.decode()}")
    print(f"  Errors: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(categories.router, prefix="/api/categories")
app.include_router(products.router, prefix="/api/products")
app.include_router(upload.router, prefix="/api/upload")
app.include_router(colors.router, prefix="/api/colors")
app.include_router(catalog.router, prefix="/api/catalog")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(sales.router, prefix="/api/sales")
app.include_router(customers.router, prefix="/api/customers")
app.include_router(layaways.router, prefix="/api/layaways")
