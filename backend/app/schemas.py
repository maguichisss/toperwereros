from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CategoryBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class ColorCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str
    hex: str


class ColorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    hex: str


class ProductBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    name: str
    code: str
    stock: int = 1
    description: str | None = None
    ubicacion: str | None = None
    price: Decimal
    image_url: str | None = None
    category_ids: list[int] = []
    color_ids: list[int] = []


class ProductCreate(ProductBase):
    pass


class ProductResponse(BaseModel):
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


class CategoryName(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class ColorName(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    hex: str

class ProductListItem(BaseModel):
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

class ProductListResponse(BaseModel):
    products: list[ProductListItem]
    total: int


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    email: str | None = None
    image_url: str | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    role_id: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str | None = None
    image_url: str | None = None
    active: bool
    role_id: int
    role_name: str | None = None
    created_at: datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class SaleCreate(BaseModel):
    items: list[SaleItemCreate]


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str | None = None
    product_code: str | None = None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total: Decimal
    created_by: int | None = None
    created_by_name: str | None = None
    created_at: datetime
    items: list[SaleItemResponse]


class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    created_at: datetime


class LayawayItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class LayawayCreate(BaseModel):
    customer_id: int | None = None
    customer: CustomerCreate | None = None
    deposit: Decimal
    items: list[LayawayItemCreate]
    notes: str | None = None


class LayawayItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str | None = None
    product_code: str | None = None


class LayawayPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: Decimal
    created_at: datetime


class LayawayResponse(BaseModel):
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
    layaways: list[LayawayResponse]
    total: int


class PaymentCreate(BaseModel):
    amount: Decimal
