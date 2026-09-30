"""Sales endpoints — create, list, and retrieve sales with stock validation."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Product, Sale, SaleItem, User
from app.schemas import SaleCreate, SaleResponse, SaleListResponse, SaleItemResponse
from app.auth import require_permission
from app.config import get_rate_limit_key
from app.query_filters import (
    SALE_BASIC,
    SALE_FIELDS,
    apply_filters,
    fetch_page,
    json_response,
    parse_date_range,
    parse_filters,
    parse_projection,
    project_rows,
    resolve_pagination,
)

logger = logging.getLogger(__name__)

router = APIRouter()

limiter = Limiter(key_func=get_rate_limit_key)


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


@router.get("", response_model=SaleListResponse, tags=["Sales"], summary="List sales",
              description="Paginated list of sales, newest first. Each sale includes line items and creator username.")
def list_sales(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    start_date: str | None = Query(None, description="Start date YYYY-MM-DD (inclusive)"),
    end_date: str | None = Query(None, description="End date YYYY-MM-DD (inclusive)"),
    skip: int | None = Query(None, ge=0, description="Number of records to skip (DSL pagination)"),
    limit: int | None = Query(None, ge=1, le=200, description="Max records to return (DSL pagination)"),
    modo: str | None = Query(None, pattern="^(basico|detallado)$", description="Projection mode: basico or detallado"),
    campos: str | None = Query(None, description="Comma-separated fields to return"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sale.view")),
) -> list[SaleResponse]:
    """Return a paginated list of sales, newest first.

    Each sale is serialized with its line items and creator username.
    Supports the shared query DSL for operator filters and projection.

    Args:
        page: 1-indexed page number (default 1).
        per_page: Items per page, 1–100 (default 20).
        start_date: Optional start date filter (YYYY-MM-DD, inclusive).
        end_date: Optional end date filter (YYYY-MM-DD, inclusive).
        skip: Number of records to skip (overrides ``page``/``per_page``).
        limit: Maximum records to return (overrides ``per_page``).
        modo: Projection mode, ``basico`` or ``detallado``.
        campos: Comma-separated fields to project.
        request: Raw request for extracting operator query params.
        db: Active database session.
        current_user: Authenticated user with ``sale.view`` permission.

    Returns:
        SaleListResponse with ``sales`` list and ``total`` count.

    Raises:
        HTTPException: 400 if ``start_date``/``end_date`` is not YYYY-MM-DD.
        HTTPException: 500 on unexpected database errors.
    """

    params = {k: v for k, v in request.query_params.multi_items()}
    parsed = parse_filters(params, SALE_FIELDS)
    projection = parse_projection(modo, campos, SALE_FIELDS, SALE_BASIC)
    range_start, range_end = parse_date_range(start_date, end_date)

    try:
        stmt = db.query(Sale)
        if range_start is not None:
            stmt = stmt.where(Sale.created_at >= range_start)
        if range_end is not None:
            stmt = stmt.where(Sale.created_at < range_end)
        stmt = apply_filters(stmt, parsed)
        offset, limit_count = resolve_pagination(
            skip=skip, limit=limit, page=page, per_page=per_page
        )
        if projection is not None and projection.active:
            rows, total = fetch_page(stmt, Sale, Sale.created_at, offset, limit_count)
            return json_response({"sales": project_rows(rows, projection), "total": total})
        eager = stmt.options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.creator),
        )
        sales, total = fetch_page(eager, Sale, Sale.created_at, offset, limit_count)
    except Exception:
        logger.exception("Failed to list sales")
        raise HTTPException(500, "Error fetching sales")
    return SaleListResponse(sales=[serialize_sale(s) for s in sales], total=total)


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
        raise HTTPException(500, "Error fetching sale")
    if not sale:
        raise HTTPException(404, "Sale not found")
    return serialize_sale(sale)


@router.post("", response_model=SaleResponse, status_code=201, tags=["Sales"], summary="Create sale",
              description="Create a new sale. Atomic stock decrement via savepoint. Unit price is captured from the product at sale time. created_by tracks the authenticated user.")
@limiter.limit("20/minute")
def create_sale(
    request: Request,
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
        raise HTTPException(400, "The sale must have at least one item")

    total = Decimal("0.00")
    sale_items = []

    try:
        with db.begin_nested():
            for item in data.items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                if not product:
                    raise HTTPException(404, f"Product {item.product_id} not found")
                if product.stock < item.quantity:
                    raise HTTPException(400, f"Insufficient stock for '{product.name}': {product.stock} available, {item.quantity} requested")

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
        raise HTTPException(500, "Error processing sale. Stock not deducted.")
