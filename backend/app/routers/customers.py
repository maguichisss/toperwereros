from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerResponse

router = APIRouter()


@router.get("")
def list_customers(q: str | None = Query(None), db: Session = Depends(get_db)):
    query = db.query(Customer)
    if q:
        query = query.filter(
            Customer.name.ilike(f"%{q}%") | Customer.phone.ilike(f"%{q}%")
        )
    customers = query.order_by(Customer.name.asc()).all()
    return customers


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    return customer


@router.post("", status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{customer_id}")
def update_customer(customer_id: int, data: CustomerCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    customer.name = data.name
    customer.phone = data.phone
    customer.email = data.email
    customer.notes = data.notes
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
    db.delete(customer)
    db.commit()
    return {"ok": True}
