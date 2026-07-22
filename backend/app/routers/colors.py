"""Color CRUD endpoints with hex-code validation."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Color, product_colors, User
from app.schemas import ColorCreate, ColorResponse
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@router.get("", response_model=list[ColorResponse], tags=["Colors"], summary="List colors",
              description="Return all colors ordered alphabetically.")
def list_colors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("color.view")),
) -> list[Color]:
    """Return all colors ordered alphabetically.

    Args:
        db: Active database session.
        current_user: Authenticated user with ``color.view`` permission.

    Returns:
        List of Color records.
    """

    return db.query(Color).order_by(Color.name).all()


@router.post("", response_model=ColorResponse, status_code=201, tags=["Colors"], summary="Create color",
              description="Create a new color. Name must be unique. Hex must match #RRGGBB format.")
def create_color(
    data: ColorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("color.create")),
) -> Color:
    """Create a new color with a valid ``#RRGGBB`` hex code.

    Args:
        data: Color creation payload with name and hex.
        db: Active database session.
        current_user: Authenticated user with ``color.create`` permission.

    Returns:
        The newly created Color record.

    Raises:
        HTTPException: 400 if name is empty or hex is invalid.
        HTTPException: 409 if a color with the same name already exists.
    """

    name = data.name.strip()
    hex_val = data.hex.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    if not HEX_RE.match(hex_val):
        raise HTTPException(400, "El color hexadecimal debe tener formato #RRGGBB")
    existing = db.query(Color).filter(Color.name == name).first()
    if existing:
        raise HTTPException(409, f"El color '{name}' ya existe")
    color = Color(name=name, hex=hex_val)
    db.add(color)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Duplicate color name on create: '%s'", name)
        raise HTTPException(409, f"El color '{name}' ya existe")
    db.refresh(color)
    return color


@router.put("/{color_id}", response_model=ColorResponse, tags=["Colors"], summary="Update color",
              description="Update a color's name and hex code. Both must be valid and unique.")
def update_color(
    color_id: int,
    data: ColorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("color.edit")),
) -> Color:
    """Update an existing color's name and hex code.

    Args:
        color_id: ID of the color to update.
        data: Updated color data.
        db: Active database session.
        current_user: Authenticated user with ``color.edit`` permission.

    Returns:
        The updated Color record.

    Raises:
        HTTPException: 404 if the color is not found.
        HTTPException: 400 if name is empty or hex is invalid.
        HTTPException: 409 if another color already uses the given name.
    """

    name = data.name.strip()
    hex_val = data.hex.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    if not HEX_RE.match(hex_val):
        raise HTTPException(400, "El color hexadecimal debe tener formato #RRGGBB")
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "Color no encontrado")
    conflict = db.query(Color).filter(Color.name == name, Color.id != color_id).first()
    if conflict:
        raise HTTPException(409, f"El color '{name}' ya existe")
    color.name = name
    color.hex = hex_val
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Duplicate color name on update: '%s' (id=%d)", name, color_id)
        raise HTTPException(409, f"El color '{name}' ya existe")
    db.refresh(color)
    return color


@router.delete("/{color_id}", status_code=204, tags=["Colors"], summary="Delete color",
              description="Delete a color. Blocked with 409 if the color is assigned to any product.")
def delete_color(
    color_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("color.delete")),
) -> None:
    """Delete a color that is not assigned to any product.

    Args:
        color_id: ID of the color to delete.
        db: Active database session.
        current_user: Authenticated user with ``color.delete`` permission.

    Raises:
        HTTPException: 404 if the color is not found.
        HTTPException: 409 if the color is assigned to one or more products.
    """

    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "Color no encontrado")
    in_use = db.execute(
        select(product_colors).where(product_colors.c.color_id == color_id)
    ).first()
    if in_use:
        raise HTTPException(
            409, "No se puede eliminar un color asignado a productos"
        )
    db.delete(color)
    db.commit()
