"""Sales endpoints — create, list, and retrieve sales with stock validation."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Product, Sale, SaleItem, User
from app.schemas import SaleCreate, SaleResponse, SaleItemResponse
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


def serialize_sale(sale: Sale) -> SaleResponse:
    """Serialize a fully-loaded Sale ORM object to a SaleResponse.

    Args:
        sale: A Sale record with ``items``, ``items.product``, and ``creator``
            eagerly loaded via ``selectinload``.

    Returns:
        SaleResponse containing the sale summary and line items.
    """

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


@router.get("", response_model=list[SaleResponse], tags=["Sales"], summary="List sales",
              description="Paginated list of sales, newest first. Each sale includes line items and creator username.")
def list_sales(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    start_date: str | None = Query(None, description="Start date YYYY-MM-DD (inclusive)"),
    end_date: str | None = Query(None, description="End date YYYY-MM-DD (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sale.view")),
) -> list[SaleResponse]:
    """Return a paginated list of sales, newest first.

    Each sale is serialized with its line items and creator username.

    Args:
        page: 1-indexed page number (default 1).
        per_page: Items per page, 1–100 (default 20).
        start_date: Optional start date filter (YYYY-MM-DD, inclusive).
        end_date: Optional end date filter (YYYY-MM-DD, inclusive).
        db: Active database session.
        current_user: Authenticated user with ``sale.view`` permission.

    Returns:
        List of serialized SaleResponse objects.

    Raises:
        HTTPException: 500 on unexpected database errors.
    """

    try:
        stmt = db.query(Sale)
        if start_date:
            dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(Sale.created_at >= dt)
        if end_date:
            dt = datetime.fromisoformat(end_date) + timedelta(days=1)
            stmt = stmt.where(Sale.created_at < dt)
        total = stmt.count()
        sales = (
            stmt
            .options(
                selectinload(Sale.items).selectinload(SaleItem.product),
                selectinload(Sale.creator),
            )
            .order_by(Sale.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    except Exception:
        logger.exception("Failed to list sales")
        raise HTTPException(500, "Error al obtener las ventas")
    return [serialize_sale(s) for s in sales]


@router.get("/{sale_id}", response_model=SaleResponse, tags=["Sales"], summary="Get sale",
              description="Return a single sale by ID with all line items and product details.")
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sale.view")),
) -> SaleResponse:
    """Return a single sale by ID with all line items.

    Args:
        sale_id: ID of the sale to retrieve.
        db: Active database session.
        current_user: Authenticated user with ``sale.view`` permission.

    Returns:
        Serialized SaleResponse.

    Raises:
        HTTPException: 404 if the sale is not found.
    """

    try:
        sale = (
            db.query(Sale)
            .options(
                selectinload(Sale.items).selectinload(SaleItem.product),
                selectinload(Sale.creator),
            )
            .filter(Sale.id == sale_id)
            .first()
        )
    except Exception:
        logger.exception("Failed to get sale %d", sale_id)
        raise HTTPException(500, "Error al obtener la venta")
    if not sale:
        raise HTTPException(404, "Venta no encontrada")
    return serialize_sale(sale)


@router.post("", response_model=SaleResponse, status_code=201, tags=["Sales"], summary="Create sale",
              description="Create a new sale. Atomic stock decrement via savepoint. Unit price is captured from the product at sale time. created_by tracks the authenticated user.")
def create_sale(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sale.create")),
) -> SaleResponse:
    """Create a new sale, decrementing product stock for each line item.

    Stock decrement and sale creation are wrapped in a savepoint so that if
    any validation fails, no stock changes are persisted.

    Args:
        data: Sale creation payload with at least one item.
        db: Active database session.
        current_user: Authenticated user with ``sale.create`` permission.

    Returns:
        Serialized SaleResponse for the newly created sale.

    Raises:
        HTTPException: 400 if the sale has no items or stock is insufficient.
        HTTPException: 404 if a referenced product does not exist.
        HTTPException: 500 on unexpected database errors.
    """

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

        db.commit()
        return serialize_sale(sale)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to create sale — rolling back stock")
        raise HTTPException(500, "Error al procesar la venta. Stock no descontado.")
