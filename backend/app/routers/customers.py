"""Customer CRUD endpoints with name/phone search."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, User
from app.schemas import CustomerCreate, CustomerResponse
from app.auth import require_permission

router = APIRouter()


def serialize_customer(c: Customer) -> dict:
    """Serialize a Customer ORM object into a JSON-safe dict.

    Args:
        c: The Customer record to serialize.

    Returns:
        Dict with ``id``, ``name``, ``phone``, ``email``, ``notes``, and
        ``created_at`` fields.
    """

    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "notes": c.notes,
        "created_at": c.created_at,
    }


@router.get("", response_model=list[CustomerResponse], tags=["Customers"], summary="List customers",
              description="Return all customers, optionally filtered by name or phone (ILIKE search).")
def list_customers(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.view")),
) -> list[dict]:
    """Return all customers, optionally filtered by name or phone.

    Args:
        q: Optional search string to match against ``name`` or ``phone``.
        db: Active database session.
        current_user: Authenticated user with ``customer.view`` permission.

    Returns:
        List of serialized Customer dicts.
    """

    query = db.query(Customer)
    if q:
        query = query.filter(
            Customer.name.ilike(f"%{q}%") | Customer.phone.ilike(f"%{q}%")
        )
    customers = query.order_by(Customer.name.asc()).all()
    return [serialize_customer(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerResponse, tags=["Customers"], summary="Get customer",
              description="Return a single customer by ID.")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.view")),
) -> dict:
    """Return a single customer by ID.

    Args:
        customer_id: ID of the customer to retrieve.
        db: Active database session.
        current_user: Authenticated user with ``customer.view`` permission.

    Returns:
        Serialized Customer dict.

    Raises:
        HTTPException: 404 if the customer is not found.
    """

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    return serialize_customer(customer)


@router.post("", response_model=CustomerResponse, status_code=201, tags=["Customers"], summary="Create customer",
              description="Create a new customer record with name, phone, email, and notes.")
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.create")),
) -> dict:
    """Create a new customer record.

    Args:
        data: Customer creation payload.
        db: Active database session.
        current_user: Authenticated user with ``customer.create`` permission.

    Returns:
        Serialized Customer dict for the newly created customer.
    """

    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return serialize_customer(customer)


@router.put("/{customer_id}", response_model=CustomerResponse, tags=["Customers"], summary="Update customer",
              description="Update an existing customer's profile fields.")
def update_customer(
    customer_id: int,
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.edit")),
) -> dict:
    """Update an existing customer's profile fields.

    Args:
        customer_id: ID of the customer to update.
        data: Updated customer data.
        db: Active database session.
        current_user: Authenticated user with ``customer.edit`` permission.

    Returns:
        Serialized Customer dict for the updated customer.

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
    db.commit()
    db.refresh(customer)
    return serialize_customer(customer)


@router.delete("/{customer_id}", tags=["Customers"], summary="Delete customer",
              description="Delete a customer record.")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer.delete")),
) -> dict[str, bool]:
    """Delete a customer record.

    Args:
        customer_id: ID of the customer to delete.
        db: Active database session.
        current_user: Authenticated user with ``customer.delete`` permission.

    Returns:
        ``{"ok": True}`` on success.

    Raises:
        HTTPException: 404 if the customer is not found.
    """

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    db.delete(customer)
    db.commit()
    return {"ok": True}
