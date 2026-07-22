"""Layaway (apartado) CRUD — create, list, add payments, cancel, and complete."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Product,
    Customer,
    Sale,
    SaleItem,
    Layaway,
    LayawayItem,
    LayawayPayment,
    User,
)
from app.schemas import (
    LayawayCreate,
    LayawayResponse,
    LayawayItemResponse,
    LayawayPaymentResponse,
    LayawayListResponse,
    PaymentCreate,
)
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


def serialize_layaway(layaway: Layaway) -> LayawayResponse:
    """Serialize a fully-loaded Layaway ORM object to a LayawayResponse.

    Expects ``items``, ``items.product``, ``payments``, ``customer``, and
    ``creator`` to be eagerly loaded via ``selectinload``.

    Args:
        layaway: A Layaway record with all relationships loaded.

    Returns:
        LayawayResponse with items, payments, and customer name.
    """

    items = layaway.items or []
    payments = layaway.payments or []
    return LayawayResponse(
        id=layaway.id,
        customer_id=layaway.customer_id,
        customer_name=layaway.customer.name if layaway.customer else None,
        total=layaway.total,
        deposit=layaway.deposit,
        balance=layaway.balance,
        status=layaway.status,
        sale_id=layaway.sale_id,
        notes=layaway.notes,
        created_at=layaway.created_at,
        updated_at=layaway.updated_at,
        created_by=layaway.created_by,
        created_by_name=layaway.creator.username if layaway.creator else None,
        items=[
            LayawayItemResponse(
                id=li.id,
                product_id=li.product_id,
                quantity=li.quantity,
                unit_price=li.unit_price,
                product_name=li.product.name if li.product else None,
                product_code=li.product.code if li.product else None,
            )
            for li in items
        ],
        payments=[
            LayawayPaymentResponse(
                id=lp.id,
                amount=lp.amount,
                created_at=lp.created_at,
            )
            for lp in payments
        ],
    )


@router.post("", response_model=LayawayResponse, status_code=201, tags=["Layaways"], summary="Create layaway",
              description="Create a new layaway (apartado). Provide customer_id or inline customer object. Deposit locks in prices and decrements stock. Initial deposit is recorded as the first payment.")
def create_layaway(
    data: LayawayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.create")),
) -> LayawayResponse:
    """Create a new layaway, decrementing product stock for each item.

    Either ``customer_id`` (existing customer) or ``customer`` (new customer)
    must be provided, but not both.  The deposit must be positive and must not
    exceed the total.

    Args:
        data: Layaway creation payload with items and deposit.
        db: Active database session.
        current_user: Authenticated user with ``apartado.create`` permission.

    Returns:
        Serialized LayawayResponse for the newly created layaway.

    Raises:
        HTTPException: 400 if the layaway has no items, customer is missing or
            ambiguous, deposit is invalid, or stock is insufficient.
        HTTPException: 404 if a referenced product or customer is not found.
    """

    if not data.items:
        raise HTTPException(400, "El apartado debe tener al menos un artículo")

    if data.customer_id and data.customer:
        raise HTTPException(400, "Proporcione customer_id o customer, no ambos")
    if not data.customer_id and not data.customer:
        raise HTTPException(400, "Debe proporcionar un cliente existente o crear uno nuevo")

    if data.deposit <= 0:
        raise HTTPException(400, "El depósito debe ser mayor a cero")

    if data.customer:
        customer = Customer(
            name=data.customer.name,
            phone=data.customer.phone,
            email=data.customer.email,
            notes=data.customer.notes,
        )
        db.add(customer)
        db.flush()
        customer_id = customer.id
    else:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer:
            raise HTTPException(404, "Cliente no encontrado")
        customer_id = data.customer_id

    total = Decimal("0.00")
    layaway_items = []

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

                layaway_items.append(LayawayItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=unit_price,
                ))

            if data.deposit > total:
                raise HTTPException(400, "El depósito no puede exceder el total")

            balance = total - data.deposit

            layaway = Layaway(
                customer_id=customer_id,
                total=total,
                deposit=data.deposit,
                balance=balance,
                status="active",
                notes=data.notes,
                created_by=current_user.id,
                items=layaway_items,
            )
            db.add(layaway)

        db.flush()

        payment = LayawayPayment(layaway_id=layaway.id, amount=data.deposit)
        db.add(payment)

        db.commit()
        db.refresh(layaway)
        db.refresh(layaway, attribute_names=["items", "payments", "customer"])
        for li in layaway.items:
            db.refresh(li, attribute_names=["product"])

        return serialize_layaway(layaway)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to create layaway for customer_id=%s", customer_id)
        raise HTTPException(500, "Error al crear el apartado")


@router.get("", response_model=LayawayListResponse, tags=["Layaways"], summary="List layaways",
              description="Paginated list of layaways. Filter by status (active/completed/cancelled) and customer_id.")
def list_layaways(
    status: str | None = Query(None),
    customer_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.view")),
) -> LayawayListResponse:
    """Return a paginated list of layaways, optionally filtered by status and/or customer.

    Args:
        status: Filter by layaway status (e.g. ``active``, ``completed``,
            ``cancelled``).
        customer_id: Filter by customer ID.
        page: 1-indexed page number (default 1).
        per_page: Items per page, 1–100 (default 20).
        db: Active database session.
        current_user: Authenticated user with ``apartado.view`` permission.

    Returns:
        LayawayListResponse with ``layaways`` list and ``total`` count.
    """

    query = db.query(Layaway)
    if status:
        query = query.filter(Layaway.status == status)
    if customer_id:
        query = query.filter(Layaway.customer_id == customer_id)

    total = query.count()
    layaways = (
        query.options(
            selectinload(Layaway.items).selectinload(LayawayItem.product),
            selectinload(Layaway.payments),
            selectinload(Layaway.customer),
            selectinload(Layaway.creator),
        )
        .order_by(Layaway.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return LayawayListResponse(
        layaways=[serialize_layaway(l) for l in layaways],
        total=total,
    )


@router.get("/{layaway_id}", response_model=LayawayResponse, tags=["Layaways"], summary="Get layaway",
              description="Return a single layaway by ID with items, payments, and customer info.")
def get_layaway(
    layaway_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.view")),
) -> LayawayResponse:
    """Return a single layaway by ID with all items, payments, and customer info.

    Args:
        layaway_id: ID of the layaway to retrieve.
        db: Active database session.
        current_user: Authenticated user with ``apartado.view`` permission.

    Returns:
        Serialized LayawayResponse.

    Raises:
        HTTPException: 404 if the layaway is not found.
    """

    layaway = (
        db.query(Layaway)
        .options(
            selectinload(Layaway.items).selectinload(LayawayItem.product),
            selectinload(Layaway.payments),
            selectinload(Layaway.customer),
            selectinload(Layaway.creator),
        )
        .filter(Layaway.id == layaway_id)
        .first()
    )
    if not layaway:
        raise HTTPException(404, "Apartado no encontrado")
    return serialize_layaway(layaway)


@router.post("/{layaway_id}/payments", response_model=LayawayResponse, status_code=201, tags=["Layaways"], summary="Add payment",
              description="Add a payment to an active layaway. Amount cannot exceed the outstanding balance. Automatically completes when balance reaches $0.")
def add_payment(
    layaway_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.edit")),
) -> LayawayResponse:
    """Add a payment to an active layaway and reduce the outstanding balance.

    When the remaining balance reaches zero the layaway is automatically
    completed and a corresponding Sale is created.

    Args:
        layaway_id: ID of the layaway to add a payment to.
        data: Payment payload with a positive ``amount``.
        db: Active database session.
        current_user: Authenticated user with ``apartado.edit`` permission.

    Returns:
        Updated LayawayResponse with new payment recorded.

    Raises:
        HTTPException: 404 if the layaway is not found.
        HTTPException: 400 if the layaway is not active, amount is not
            positive, or amount exceeds the outstanding balance.
    """

    layaway = (
        db.query(Layaway)
        .options(
            selectinload(Layaway.items).selectinload(LayawayItem.product),
            selectinload(Layaway.payments),
            selectinload(Layaway.customer),
            selectinload(Layaway.creator),
        )
        .filter(Layaway.id == layaway_id)
        .first()
    )
    if not layaway:
        raise HTTPException(404, "Apartado no encontrado")
    if layaway.status != "active":
        raise HTTPException(400, "Solo se pueden agregar abonos a apartados activos")
    if data.amount <= 0:
        raise HTTPException(400, "El abono debe ser mayor a cero")
    if data.amount > layaway.balance:
        raise HTTPException(400, f"El abono excede el saldo pendiente: ${layaway.balance}")

    payment = LayawayPayment(layaway_id=layaway.id, amount=data.amount)
    db.add(payment)
    layaway.balance -= data.amount

    if layaway.balance <= 0:
        complete_layaway(layaway, db, current_user)

    db.commit()
    db.refresh(layaway, attribute_names=["items", "payments", "customer"])
    for li in layaway.items:
        db.refresh(li, attribute_names=["product"])

    return serialize_layaway(layaway)


@router.patch("/{layaway_id}/cancel", response_model=LayawayResponse, tags=["Layaways"], summary="Cancel layaway",
              description="Cancel an active layaway and restore all product stock.")
def cancel_layaway(
    layaway_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.edit")),
) -> LayawayResponse:
    """Cancel an active layaway and restore product stock.

    Args:
        layaway_id: ID of the layaway to cancel.
        db: Active database session.
        current_user: Authenticated user with ``apartado.edit`` permission.

    Returns:
        Updated LayawayResponse with status set to ``cancelled``.

    Raises:
        HTTPException: 404 if the layaway is not found.
        HTTPException: 400 if the layaway is not active.
    """

    layaway = (
        db.query(Layaway)
        .options(
            selectinload(Layaway.items).selectinload(LayawayItem.product),
            selectinload(Layaway.payments),
            selectinload(Layaway.customer),
            selectinload(Layaway.creator),
        )
        .filter(Layaway.id == layaway_id)
        .first()
    )
    if not layaway:
        raise HTTPException(404, "Apartado no encontrado")
    if layaway.status != "active":
        raise HTTPException(400, "Solo se pueden cancelar apartados activos")

    for li in layaway.items:
        product = db.query(Product).filter(Product.id == li.product_id).first()
        if product:
            product.stock += li.quantity

    layaway.status = "cancelled"
    db.commit()
    db.refresh(layaway, attribute_names=["items", "payments", "customer"])
    for li in layaway.items:
        db.refresh(li, attribute_names=["product"])

    return serialize_layaway(layaway)


@router.patch("/{layaway_id}/complete", response_model=LayawayResponse, tags=["Layaways"], summary="Complete layaway",
              description="Manually complete an active layaway, creating a linked Sale record. Idempotent if already completed.")
def complete_layaway_endpoint(
    layaway_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("apartado.edit")),
) -> LayawayResponse:
    """Manually complete an active layaway, creating a corresponding Sale.

    This is the manual equivalent of automatic completion triggered by
    ``add_payment`` when the balance reaches zero.

    Args:
        layaway_id: ID of the layaway to complete.
        db: Active database session.
        current_user: Authenticated user with ``apartado.edit`` permission.

    Returns:
        Updated LayawayResponse with status set to ``completed`` and ``sale_id``.

    Raises:
        HTTPException: 404 if the layaway is not found.
        HTTPException: 400 if the layaway is not active.
    """

    layaway = (
        db.query(Layaway)
        .options(
            selectinload(Layaway.items).selectinload(LayawayItem.product),
            selectinload(Layaway.payments),
            selectinload(Layaway.customer),
            selectinload(Layaway.creator),
        )
        .filter(Layaway.id == layaway_id)
        .first()
    )
    if not layaway:
        raise HTTPException(404, "Apartado no encontrado")
    if layaway.status != "active":
        raise HTTPException(400, "Solo se pueden completar apartados activos")

    complete_layaway(layaway, db, current_user)
    db.commit()
    db.refresh(layaway, attribute_names=["items", "payments", "customer"])
    for li in layaway.items:
        db.refresh(li, attribute_names=["product"])

    return serialize_layaway(layaway)


def complete_layaway(
    layaway: Layaway,
    db: Session,
    current_user: User | None = None,
) -> None:
    """Mark a layaway as completed and create a linked Sale.

    Idempotent: if the layaway already has a ``sale_id`` this is a no-op.

    Args:
        layaway: The Layaway ORM object to complete.
        db: Active database session.
        current_user: The user completing the layaway (used as ``created_by``
            on the generated Sale).
    """

    if layaway.sale_id:
        return

    sale_items = []
    for li in layaway.items:
        sale_items.append(SaleItem(
            product_id=li.product_id,
            quantity=li.quantity,
            unit_price=li.unit_price,
        ))

    created_by = current_user.id if current_user else None
    sale = Sale(total=layaway.total, items=sale_items, created_by=created_by)
    db.add(sale)
    db.flush()

    layaway.sale_id = sale.id
    layaway.status = "completed"
    if layaway.balance < 0:
        layaway.balance = Decimal("0.00")
