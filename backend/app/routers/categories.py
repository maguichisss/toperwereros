from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import Category, product_categories, User
from app.schemas import CategoryCreate, CategoryResponse
from app.auth import require_permission

router = APIRouter()


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(require_permission("category.view"))):
    return db.query(Category).order_by(Category.name).all()


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("category.create"))):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(409, "Category already exists")
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("category.edit"))):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")
    conflict = db.query(Category).filter(Category.name == name, Category.id != category_id).first()
    if conflict:
        raise HTTPException(409, "Category name already taken")
    category.name = name
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_permission("category.delete"))):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")
    in_use = db.execute(
        select(product_categories).where(product_categories.c.category_id == category_id)
    ).first()
    if in_use:
        raise HTTPException(
            409, "No se puede eliminar una categoría asignada a productos"
        )
    db.delete(category)
    db.commit()
