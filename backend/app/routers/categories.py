"""Category CRUD endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, product_categories, User
from app.schemas import CategoryCreate, CategoryResponse
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[CategoryResponse], tags=["Categories"], summary="List categories",
              description="Return all categories ordered alphabetically.")
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.view")),
) -> list[Category]:
    """Return all categories ordered alphabetically.

    Args:
        db: Active database session.
        current_user: Authenticated user with ``category.view`` permission.

    Returns:
        List of Category records.

    Raises:
        HTTPException: 403 if the user lacks ``category.view`` permission.
    """

    return db.query(Category).order_by(Category.name).all()


@router.post("", response_model=CategoryResponse, status_code=201, tags=["Categories"], summary="Create category",
              description="Create a new category. Name must be non-empty and unique.")
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.create")),
) -> Category:
    """Create a new category.

    Args:
        data: Category creation payload with name.
        db: Active database session.
        current_user: Authenticated user with ``category.create`` permission.

    Returns:
        The newly created Category record.

    Raises:
        HTTPException: 400 if the name is empty.
        HTTPException: 409 if a category with the same name already exists.
    """

    name = data.name.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(409, "La categoría ya fue creada")
    category = Category(name=name)
    db.add(category)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create category")
        raise HTTPException(500, "Error al crear la categoría")
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse, tags=["Categories"], summary="Update category",
              description="Update a category's name. New name must be unique.")
def update_category(
    category_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.edit")),
) -> Category:
    """Update an existing category's name.

    Args:
        category_id: ID of the category to update.
        data: Updated category data.
        db: Active database session.
        current_user: Authenticated user with ``category.edit`` permission.

    Returns:
        The updated Category record.

    Raises:
        HTTPException: 404 if the category is not found.
        HTTPException: 400 if the name is empty.
        HTTPException: 409 if another category already uses the given name.
    """

    name = data.name.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "Categoría no encontrada")
    conflict = db.query(Category).filter(Category.name == name, Category.id != category_id).first()
    if conflict:
        raise HTTPException(409, "La categoría ya fue creada")
    category.name = name
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update category %d", category_id)
        raise HTTPException(500, "Error al actualizar la categoría")
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204, tags=["Categories"], summary="Delete category",
              description="Delete a category. Blocked with 409 if the category is assigned to any product.")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.delete")),
) -> None:
    """Delete a category that is not assigned to any product.

    Args:
        category_id: ID of the category to delete.
        db: Active database session.
        current_user: Authenticated user with ``category.delete`` permission.

    Returns:
        ``None`` (204 No Content on success).

    Raises:
        HTTPException: 404 if the category is not found.
        HTTPException: 409 if the category is assigned to one or more products.
        HTTPException: 500 on unexpected database errors.
    """

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "Categoría no encontrada")
    in_use = db.execute(
        select(product_categories).where(product_categories.c.category_id == category_id)
    ).first()
    if in_use:
        raise HTTPException(
            409, "No se puede eliminar una categoría asignada a productos"
        )
    db.delete(category)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to delete category %d", category_id)
        raise HTTPException(500, "Error al eliminar la categoría")
