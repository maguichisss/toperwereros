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
    price: Decimal
    image_url: str | None = None
    category_id: int
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
    price: Decimal
    image_url: str | None = None
    category_id: int
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse
    colors: list[ColorResponse] = []
