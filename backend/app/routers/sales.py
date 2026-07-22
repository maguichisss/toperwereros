from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models import Product, Sale, SaleItem, User
from app.schemas import SaleCreate, SaleResponse, SaleItemResponse
from app.auth import require_permission

router = APIRouter()


def serialize_sale(sale):
    items = sale.items or []
    return SaleResponse(
        id=sale.id,
        total=sale.total,
        created_by=sale.created_by,
        created_by_name=sale.creator.username if sale.creator else None,
        created_at=sale.created_at,
        items=[
            SaleItemResponse(
                id=si.id,
                product_id=si.product_id,
                quantity=si.quantity,
                unit_price=si.unit_price,
                product_name=si.product.name if si.product else None,
                product_code=si.product.code if si.product else None,
            )
            for si in items
        ],
    )


@router.get("")
def list_sales(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sale.view")),
):
    total = db.query(Sale).count()
    sales = (
        db.query(Sale)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.creator),
        )
        .order_by(Sale.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [serialize_sale(s) for s in sales]


@router.get("/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sale.view"))):
    sale = (
        db.query(Sale)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.creator),
        )
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(404, "Venta no encontrada")
    return serialize_sale(sale)


@router.post("", status_code=201)
def create_sale(data: SaleCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sale.create"))):
    if not data.items:
        raise HTTPException(400, "La venta debe tener al menos un artículo")

    total = Decimal("0.00")
    sale_items = []

    try:
        with db.begin_nested():
            for item in data.items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                if not product:
                    raise HTTPException(404, f"Producto {item.product_id} no encontrado")
                if product.stock < item.quantity:
                    raise HTTPException(400, f"Stock insuficiente para '{product.name}': {product.stock} disponible(s), {item.quantity} solicitado(s)")

                unit_price = product.price
                total += unit_price * item.quantity
                product.stock -= item.quantity

                sale_items.append(SaleItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=unit_price,
                ))

            sale = Sale(total=total, items=sale_items, created_by=current_user.id)
            db.add(sale)

        db.flush()
        db.refresh(sale, attribute_names=["items"])
        for si in sale.items:
            db.refresh(si, attribute_names=["product"])

        return serialize_sale(sale)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "Error al procesar la venta. Stock no descontado.")
