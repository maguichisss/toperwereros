from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Color
from app.schemas import ColorResponse

router = APIRouter()


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.name).all()
