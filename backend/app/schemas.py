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
