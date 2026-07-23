"""Customer CRUD endpoints with name/phone search."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import escape_like
from app.models import Customer, User
from app.schemas import CustomerCreate, CustomerResponse
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[CustomerResponse], tags=["Customers"], summary="List customers",
              description="Return all customers, optionally filtered by name or phone (ILIKE search).")
def list_customers(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.view")),
) -> list[Customer]:
    """Return all customers, optionally filtered by name or phone.

    Args:
        q: Optional search string to match against ``name`` or ``phone``.
        db: Active database session.
        current_user: Authenticated user with ``customer.view`` permission.

    Returns:
        List of Customer records.
    """

    query = db.query(Customer)
    if q:
        pattern = f"%{escape_like(q)}%"
        query = query.filter(
            Customer.name.ilike(pattern, escape="\\") | Customer.phone.ilike(pattern, escape="\\")
        )
    return query.order_by(Customer.name.asc()).all()


@router.get("/{customer_id}", response_model=CustomerResponse, tags=["Customers"], summary="Get customer",
              description="Return a single customer by ID.")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.view")),
) -> Customer:
    """Return a single customer by ID.

    Args:
        customer_id: ID of the customer to retrieve.
        db: Active database session.
        current_user: Authenticated user with ``customer.view`` permission.

    Returns:
        Customer record.

    Raises:
        HTTPException: 404 if the customer is not found.
    """

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    return customer


@router.post("", response_model=CustomerResponse, status_code=201, tags=["Customers"], summary="Create customer",
              description="Create a new customer record with name, phone, email, and notes.")
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.create")),
) -> Customer:
    """Create a new customer record.

    Args:
        data: Customer creation payload.
        db: Active database session.
        current_user: Authenticated user with ``customer.create`` permission.

    Returns:
        The newly created Customer record.
    """

    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
    )
    db.add(customer)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create customer")
        raise HTTPException(500, "Error al crear el cliente")
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse, tags=["Customers"], summary="Update customer",
              description="Update an existing customer's profile fields.")
def update_customer(
    customer_id: int,
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.edit")),
) -> Customer:
    """Update an existing customer's profile fields.

    Args:
        customer_id: ID of the customer to update.
        data: Updated customer data.
        db: Active database session.
        current_user: Authenticated user with ``customer.edit`` permission.

    Returns:
        The updated Customer record.

    Raises:
        HTTPException: 404 if the customer is not found.
    """

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    customer.name = data.name
    customer.phone = data.phone
    customer.email = data.email
    customer.notes = data.notes
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update customer %d", customer_id)
        raise HTTPException(500, "Error al actualizar el cliente")
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204, tags=["Customers"], summary="Delete customer",
              description="Delete a customer record.")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.delete")),
) -> None:
    """Delete a customer record.

    Args:
        customer_id: ID of the customer to delete.
        db: Active database session.
        current_user: Authenticated user with ``customer.delete`` permission.

    Raises:
        HTTPException: 404 if the customer is not found.
    """

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    db.delete(customer)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to delete customer %d", customer_id)
        raise HTTPException(500, "Error al eliminar el cliente")
