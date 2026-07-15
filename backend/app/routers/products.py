import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, String
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models import Product, Category, Color
from app.schemas import ProductCreate, ProductResponse, ProductListResponse

router = APIRouter()


@router.get("", response_model=ProductListResponse)
def list_products(
    category_ids: str | None = None,
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    export: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Product).options(
        selectinload(Product.categories),
        selectinload(Product.colors),
    )
    if category_ids:
        ids = [int(x) for x in category_ids.split(",")]
        query = query.filter(Product.categories.any(Category.id.in_(ids)))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Product.code.ilike(pattern),
                Product.name.ilike(pattern),
                Product.ubicacion.ilike(pattern),
                Product.price.cast(String).ilike(pattern),
                Product.categories.any(Category.name.ilike(pattern)),
                Product.colors.any(Color.name.ilike(pattern)),
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


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    code = data.code.strip()
    if not code:
        raise HTTPException(400, "Code is required")
    existing = db.query(Product).filter(Product.code == code).first()
    if existing:
        raise HTTPException(400, f"Ya existe un producto con ese código: '{existing.name}'")
    if data.price is None or data.price < 0:
        raise HTTPException(400, "Valid price is required")
    categories = []
    if data.category_ids:
        categories = db.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(400, "One or more categories not found")
    colors = []
    if data.color_ids:
        colors = db.query(Color).filter(Color.id.in_(data.color_ids)).all()
        if len(colors) != len(data.color_ids):
            raise HTTPException(400, "One or more colors not found")
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
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    if data.price is None or data.price < 0:
        raise HTTPException(400, "Valid price is required")
    code = data.code.strip()
    if not code:
        raise HTTPException(400, "Code is required")
    existing = db.query(Product).filter(Product.code == code, Product.id != product_id).first()
    if existing:
        raise HTTPException(400, f"Ya existe un producto con ese código: '{existing.name}'")
    colors = product.colors
    if data.color_ids is not None:
        colors = db.query(Color).filter(Color.id.in_(data.color_ids)).all()
        if len(colors) != len(data.color_ids):
            raise HTTPException(400, "One or more colors not found")
    product.name = name
    product.code = code
    product.stock = data.stock
    product.description = data.description
    product.ubicacion = data.ubicacion
    product.price = data.price
    if data.image_url != product.image_url and product.image_url:
        old_path = os.path.join(os.getcwd(), "uploads", product.image_url.replace("/uploads/", ""))
        if os.path.exists(old_path):
            os.remove(old_path)
    product.image_url = data.image_url
    if data.category_ids is not None:
        categories = db.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(400, "One or more categories not found")
        product.categories = categories
    product.colors = colors
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    if product.image_url:
        filename = product.image_url.replace("/uploads/", "")
        filepath = os.path.join(os.getcwd(), "uploads", filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            print(f"Image file not found for product {product.id}: {filepath}")

    db.delete(product)
    db.commit()
