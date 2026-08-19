"""Pydantic request/response schemas for the Store Catalog API.

All schemas use camelCase alias generation for JSON serialization while
accepting snake_case field names in Python code (via ``populate_by_name=True``).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def to_camel(s: str) -> str:
    """Convert a snake_case string to camelCase.

    Args:
        s: A snake_case identifier string.

    Returns:
        The camelCase equivalent (e.g. ``"first_name"`` -> ``"firstName"``).
    """

    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ── Categories ──────────────────────────────────────────────────────────────

class CategoryBase(BaseModel):
    """Base schema for category data with camelCase alias generation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str = Field(min_length=1, max_length=100)


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""

    pass


class CategoryResponse(BaseModel):
    """Schema for returning a category with timestamps."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


# ── Colors ──────────────────────────────────────────────────────────────────

class ColorCreate(BaseModel):
    """Schema for creating a new color with name and hex code."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str = Field(min_length=1, max_length=50)
    hex: str


class ColorResponse(BaseModel):
    """Schema for returning a color."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    hex: str


# ── Products ────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    """Base schema for product data with category and color ID lists."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    stock: int = Field(default=1, ge=0)
    description: str | None = Field(default=None, max_length=2000)
    ubicacion: str | None = Field(default=None, max_length=200)
    price: Decimal = Field(ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    category_ids: list[int] = []
    color_ids: list[int] = []


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    pass


class ProductResponse(BaseModel):
    """Schema for returning a full product with nested categories and colors."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    stock: int = 1
    description: str | None = None
    ubicacion: str | None = None
    price: Decimal
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    categories: list[CategoryResponse] = []
    colors: list[ColorResponse] = []

    @field_serializer("image_url")
    def _resolve_image_url(self, value: str | None) -> str | None:
        from app.gcs import resolve_image_url
        return resolve_image_url(value)


class CategoryName(BaseModel):
    """Minimal category representation for product list items."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ColorName(BaseModel):
    """Minimal color representation for product list items."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    hex: str


class ProductListItem(BaseModel):
    """Lightweight product representation for paginated list views."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    stock: int = 1
    ubicacion: str | None = None
    price: Decimal
    image_url: str | None = None
    updated_at: datetime
    categories: list[CategoryName] = []
    colors: list[ColorName] = []

    @field_serializer("image_url")
    def _resolve_image_url(self, value: str | None) -> str | None:
        from app.gcs import resolve_image_url
        return resolve_image_url(value)


class ProductListResponse(BaseModel):
    """Paginated product list response with total count."""

    products: list[ProductListItem]
    total: int


# ── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Schema for login credentials."""

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(min_length=12)


class ProfileUpdateRequest(BaseModel):
    """Schema for updating user profile email and image."""

    email: str | None = None
    image_url: str | None = None


class RoleCreate(BaseModel):
    """Schema for creating a new role."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str = Field(min_length=1, max_length=50)


class RoleResponse(BaseModel):
    """Schema for returning a role."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserCreate(BaseModel):
    """Schema for creating a new user account."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12)
    email: str | None = None
    role_id: int

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()


class UserUpdate(BaseModel):
    """Schema for admin updating another user's fields."""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: str | None = None
    role_id: int | None = None
    password: str | None = Field(None, min_length=12)
    active: bool | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Schema for returning user profile information."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str | None = None
    image_url: str | None = None
    active: bool
    role_id: int
    role_name: str | None = None
    created_at: datetime

    @field_serializer("image_url")
    def _resolve_image_url(self, value: str | None) -> str | None:
        from app.gcs import resolve_image_url
        return resolve_image_url(value)


# ── Sales ───────────────────────────────────────────────────────────────────

class SaleItemCreate(BaseModel):
    """Schema for a single sale line item."""

    product_id: int
    quantity: int = Field(default=1, ge=1)


class SaleCreate(BaseModel):
    """Schema for creating a new sale with one or more items."""

    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemResponse(BaseModel):
    """Schema for returning a sale line item with product details."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str | None = None
    product_code: str | None = None


class SaleResponse(BaseModel):
    """Schema for returning a complete sale with items and creator info."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    total: Decimal
    created_by: int | None = None
    created_by_name: str | None = None
    created_at: datetime
    items: list[SaleItemResponse]


# ── Customers ───────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    """Schema for creating or updating a customer."""

    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class CustomerResponse(BaseModel):
    """Schema for returning a customer record."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    created_at: datetime


# ── Layaways ────────────────────────────────────────────────────────────────

class LayawayItemCreate(BaseModel):
    """Schema for a single layaway line item."""

    product_id: int
    quantity: int = Field(default=1, ge=1)


class LayawayCreate(BaseModel):
    """Schema for creating a new layaway with deposit and items."""

    customer_id: int | None = None
    customer: CustomerCreate | None = None
    deposit: Decimal = Field(gt=0)
    items: list[LayawayItemCreate] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=2000)


class LayawayUpdate(BaseModel):
    """Schema for updating top-level layaway fields."""

    notes: str | None = Field(default=None, max_length=2000)


class LayawayItemResponse(BaseModel):
    """Schema for returning a layaway line item with product details."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str | None = None
    product_code: str | None = None


class LayawayPaymentResponse(BaseModel):
    """Schema for returning a layaway payment record."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: Decimal
    created_at: datetime


class LayawayResponse(BaseModel):
    """Schema for returning a complete layaway with items, payments, and customer info."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    customer_name: str | None = None
    total: Decimal
    deposit: Decimal
    balance: Decimal
    status: str
    sale_id: int | None = None
    created_by: int | None = None
    created_by_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[LayawayItemResponse]
    payments: list[LayawayPaymentResponse]


class LayawayListResponse(BaseModel):
    """Paginated layaway list response with total count."""

    layaways: list[LayawayResponse]
    total: int


class PaymentCreate(BaseModel):
    """Schema for adding a payment to a layaway."""

    amount: Decimal = Field(gt=0)


class LayawayItemAdd(BaseModel):
    """Schema for adding a new item to an active layaway."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    product_id: int
    quantity: int = Field(default=1, ge=1)


class LayawayItemUpdate(BaseModel):
    """Schema for updating an existing layaway item's quantity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    quantity: int = Field(ge=1)
