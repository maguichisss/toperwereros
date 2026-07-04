import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, Category, Color
from app.schemas import ProductCreate, ProductResponse

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
def list_products(category_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Product).join(Category)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    return q.order_by(Product.created_at.desc()).all()


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
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(400, "Category not found")
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
        category_id=data.category_id,
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
    if data.category_id and not db.query(Category).filter(Category.id == data.category_id).first():
        raise HTTPException(400, "Category not found")
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
    if data.image_url != product.image_url:
        if product.image_url and data.image_url:
            old_path = os.path.join(os.getcwd(), "uploads", product.image_url.lstrip("/uploads/"))
            new_path = os.path.join(os.getcwd(), "uploads", data.image_url.lstrip("/uploads/"))
            if os.path.exists(new_path) and os.path.exists(old_path):
                with open(old_path, "wb") as dst:
                    dst.write(open(new_path, "rb").read())
                product.updated_at = datetime.now()
            data.image_url = product.image_url
        elif product.image_url and not data.image_url:
            old_path = os.path.join(os.getcwd(), "uploads", product.image_url.lstrip("/uploads/"))
            if os.path.exists(old_path):
                os.remove(old_path)
    product.image_url = data.image_url
    product.category_id = data.category_id
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
        filename = product.image_url.lstrip("/uploads/")
        filepath = os.path.join(os.getcwd(), "uploads", filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            print(f"Image file not found for product {product.id}: {filepath}")

    db.delete(product)
    db.commit()
