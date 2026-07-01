import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import Color, product_colors
from app.schemas import ColorCreate, ColorResponse

router = APIRouter()

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.name).all()


@router.post("", response_model=ColorResponse, status_code=201)
def create_color(data: ColorCreate, db: Session = Depends(get_db)):
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
        raise HTTPException(409, f"El color '{name}' ya existe")
    db.refresh(color)
    return color


@router.put("/{color_id}", response_model=ColorResponse)
def update_color(color_id: int, data: ColorCreate, db: Session = Depends(get_db)):
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
        raise HTTPException(409, f"El color '{name}' ya existe")
    db.refresh(color)
    return color


@router.delete("/{color_id}", status_code=204)
def delete_color(color_id: int, db: Session = Depends(get_db)):
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
