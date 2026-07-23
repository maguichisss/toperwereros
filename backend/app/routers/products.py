"""Product CRUD with pagination, search, category/color filtering, and image cleanup."""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, String
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.config import safe_upload_path, escape_like
from app.models import Product, Category, Color, User
from app.schemas import ProductCreate, ProductResponse, ProductListResponse
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ProductListResponse, tags=["Products"], summary="List products",
              description="Paginated product list with full-text search (code, name, ubicacion, price, category, color), category filtering, and export mode.")
def list_products(
    category_ids: str | None = None,
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    export: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.view")),
) -> ProductListResponse:
    """Return a paginated, filterable product list.

    Supports full-text search across code, name, ubicacion, price, category
    name, and color name.  When ``export=True``, pagination is skipped and all
    matching products are returned.

    Args:
        category_ids: Comma-separated category IDs to filter by.
        q: Optional search string matched against multiple product fields.
        page: 1-indexed page number (default 1).
        per_page: Items per page, 1–200 (default 20).
        export: If ``True``, return all results without pagination.
        db: Active database session.
        current_user: Authenticated user with ``product.view`` permission.

    Returns:
        ProductListResponse with ``products`` list and ``total`` count.
    """

    query = db.query(Product).options(
        selectinload(Product.categories),
        selectinload(Product.colors),
    )
    if category_ids:
        ids = [int(x) for x in category_ids.split(",")]
        query = query.filter(Product.categories.any(Category.id.in_(ids)))
    if q:
        pattern = f"%{escape_like(q)}%"
        query = query.filter(
            or_(
                Product.code.ilike(pattern, escape="\\"),
                Product.name.ilike(pattern, escape="\\"),
                Product.ubicacion.ilike(pattern, escape="\\"),
                Product.price.cast(String).ilike(pattern, escape="\\"),
                Product.categories.any(Category.name.ilike(pattern, escape="\\")),
                Product.colors.any(Color.name.ilike(pattern, escape="\\")),
            )
        )
    total = query.count()
    if export:
        products = query.order_by(Product.created_at.desc()).all()
    else:
        products = (
            query.order_by(Product.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    return ProductListResponse(products=products, total=total)


@router.get("/{product_id}", response_model=ProductResponse, tags=["Products"], summary="Get product",
              description="Return a single product by ID with categories and colors loaded.")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.view")),
) -> Product:
    """Return a single product by ID with categories and colors loaded.

    Args:
        product_id: ID of the product to retrieve.
        db: Active database session.
        current_user: Authenticated user with ``product.view`` permission.

    Returns:
        Full Product record.

    Raises:
        HTTPException: 404 if the product is not found.
    """

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    return product


@router.post("", response_model=ProductResponse, status_code=201, tags=["Products"], summary="Create product",
              description="Create a new product. Requires unique code, valid price (>= 0), and existing category/color IDs.")
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.create")),
) -> Product:
    """Create a new product with optional category and color associations.

    Validates name, code, price, and that all referenced categories/colors exist.

    Args:
        data: Product creation payload.
        db: Active database session.
        current_user: Authenticated user with ``product.create`` permission.

    Returns:
        The newly created Product record.

    Raises:
        HTTPException: 400 if required fields are missing, price is invalid,
            or a referenced category/color does not exist.
        HTTPException: 400 if the product code already exists.
    """

    name = data.name.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    code = data.code.strip()
    if not code:
        raise HTTPException(400, "El código es obligatorio")
    existing = db.query(Product).filter(Product.code == code).first()
    if existing:
        raise HTTPException(400, f"Ya existe un producto con ese código: '{existing.name}'")
    if data.price is None or data.price < 0:
        raise HTTPException(400, "El precio debe ser válido")
    categories = []
    if data.category_ids:
        categories = db.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(400, "Una o más categorías no fueron encontradas")
    colors = []
    if data.color_ids:
        colors = db.query(Color).filter(Color.id.in_(data.color_ids)).all()
        if len(colors) != len(data.color_ids):
            raise HTTPException(400, "Uno o más colores no fueron encontrados")
    product = Product(
        name=name,
        code=code,
        stock=data.stock,
        description=data.description,
        ubicacion=data.ubicacion,
        price=data.price,
        image_url=data.image_url,
        categories=categories,
        colors=colors,
    )
    db.add(product)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create product")
        raise HTTPException(500, "Error al crear el producto")
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse, tags=["Products"], summary="Update product",
              description="Full product update. Old image file is deleted from disk when image_url changes.")
def update_product(
    product_id: int,
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.edit")),
) -> Product:
    """Update an existing product, replacing categories, colors, and image.

    If the image URL changes, the old image file is deleted from disk.

    Args:
        product_id: ID of the product to update.
        data: Updated product data.
        db: Active database session.
        current_user: Authenticated user with ``product.edit`` permission.

    Returns:
        The updated Product record.

    Raises:
        HTTPException: 404 if the product is not found.
        HTTPException: 400 if required fields are missing, price is invalid,
            code is taken by another product, or a referenced category/color
            does not exist.
    """

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    if data.price is None or data.price < 0:
        raise HTTPException(400, "El precio debe ser válido")
    code = data.code.strip()
    if not code:
        raise HTTPException(400, "El código es obligatorio")
    existing = db.query(Product).filter(Product.code == code, Product.id != product_id).first()
    if existing:
        raise HTTPException(400, f"Ya existe un producto con ese código: '{existing.name}'")
    colors = product.colors
    if data.color_ids is not None:
        colors = db.query(Color).filter(Color.id.in_(data.color_ids)).all()
        if len(colors) != len(data.color_ids):
            raise HTTPException(400, "Uno o más colores no fueron encontrados")
    product.name = name
    product.code = code
    product.stock = data.stock
    product.description = data.description
    product.ubicacion = data.ubicacion
    product.price = data.price
    if data.image_url != product.image_url and product.image_url:
        old_path = safe_upload_path(product.image_url)
        if old_path and os.path.exists(old_path):
            os.remove(old_path)
    product.image_url = data.image_url
    if data.category_ids is not None:
        categories = db.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(400, "Una o más categorías no fueron encontradas")
        product.categories = categories
    product.colors = colors
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update product %d", product_id)
        raise HTTPException(500, "Error al actualizar el producto")
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204, tags=["Products"], summary="Delete product",
              description="Delete a product and remove its image file from disk.")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.delete")),
) -> None:
    """Delete a product and remove its image file from disk.

    Args:
        product_id: ID of the product to delete.
        db: Active database session.
        current_user: Authenticated user with ``product.delete`` permission.

    Raises:
        HTTPException: 404 if the product is not found.
    """

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    if product.image_url:
        filepath = safe_upload_path(product.image_url)
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        else:
            logger.warning("Image file not found for product %d: %s", product.id, product.image_url)

    db.delete(product)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to delete product %d", product_id)
        raise HTTPException(500, "Error al eliminar el producto")
