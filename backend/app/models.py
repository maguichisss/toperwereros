"""SQLAlchemy ORM models and association tables for the store catalog.

Defines all database tables including products, categories, colors, users,
roles, sales, customers, and layaways (apartados).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Integer, String, Numeric, ForeignKey, DateTime, Table, Column, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


product_colors = Table(
    "product_colors",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("color_id", Integer, ForeignKey("colors.id", ondelete="CASCADE"), primary_key=True),
)
"""Association table linking products to their available colors."""

product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)
"""Association table linking products to their categories."""


class Color(Base):
    """A product color option identified by name and hex code."""

    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hex: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())


class Category(Base):
    """A product category used for grouping and filtering."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Product(Base):
    """Product catalog entry with code, pricing, and stock tracking."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ubicacion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    categories: Mapped[list["Category"]] = relationship("Category", secondary=product_categories)
    colors: Mapped[list["Color"]] = relationship("Color", secondary=product_colors, backref="products")


class Role(Base):
    """A user role that determines permission levels (admin, employee, viewer)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class User(Base):
    """A system user with credentials, role, and optional profile image."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")


class Sale(Base):
    """A completed sale transaction with line items and optional creator reference."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["SaleItem"]] = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    creator: Mapped[Optional["User"]] = relationship("User")


class SaleItem(Base):
    """A single line item within a sale, recording product, quantity, and unit price."""

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")
    product: Mapped["Product"] = relationship("Product")


class Customer(Base):
    """A customer record with contact information and optional notes."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Layaway(Base):
    """A layaway (apartado) plan tracking deposits, balance, and status."""

    __tablename__ = "layaways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    sale_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sales.id"), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    customer: Mapped["Customer"] = relationship("Customer")
    items: Mapped[list["LayawayItem"]] = relationship("LayawayItem", back_populates="layaway", cascade="all, delete-orphan")
    payments: Mapped[list["LayawayPayment"]] = relationship("LayawayPayment", back_populates="layaway", cascade="all, delete-orphan")
    sale: Mapped[Optional["Sale"]] = relationship("Sale")
    creator: Mapped[Optional["User"]] = relationship("User")


class LayawayItem(Base):
    """A line item within a layaway, recording product, quantity, and locked-in price."""

    __tablename__ = "layaway_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("layaways.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    layaway: Mapped["Layaway"] = relationship("Layaway", back_populates="items")
    product: Mapped["Product"] = relationship("Product")


class LayawayPayment(Base):
    """A deposit or installment payment toward a layaway balance."""

    __tablename__ = "layaway_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("layaways.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    layaway: Mapped["Layaway"] = relationship("Layaway", back_populates="payments")
