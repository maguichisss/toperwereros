"""Unit tests for Pydantic schema validation constraints."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    ProductCreate,
    CategoryCreate,
    ColorCreate,
    CustomerCreate,
    LoginRequest,
    UserCreate,
    SaleCreate,
    SaleItemCreate,
    LayawayCreate,
    LayawayItemCreate,
    LayawayItemAdd,
    LayawayItemUpdate,
    PaymentCreate,
)


class TestProductConstraints:
    def test_name_min_length(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="", code="P001", price=10.0)

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="x" * 201, code="P001", price=10.0)

    def test_code_min_length(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="Widget", code="", price=10.0)

    def test_stock_negative_rejected(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="Widget", code="P001", stock=-1, price=10.0)

    def test_price_negative_rejected(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="Widget", code="P001", price=-5.0)

    def test_valid_product(self):
        p = ProductCreate(name="Widget", code="P001", stock=5, price=Decimal("19.99"))
        assert p.name == "Widget"
        assert p.stock == 5

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="Widget", code="P001", price=10.0,
                description="x" * 2001,
            )


class TestCategoryConstraints:
    def test_name_empty_rejected(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="")

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="x" * 101)

    def test_valid_category(self):
        c = CategoryCreate(name="Electronics")
        assert c.name == "Electronics"


class TestColorConstraints:
    def test_name_empty_rejected(self):
        with pytest.raises(ValidationError):
            ColorCreate(name="", hex="#000000")

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            ColorCreate(name="x" * 51, hex="#000000")


class TestCustomerConstraints:
    def test_name_empty_rejected(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="")

    def test_phone_max_length(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="John", phone="x" * 21)


class TestLoginConstraints:
    def test_username_empty_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="pass")

    def test_password_empty_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="user", password="")


class TestUserCreateConstraints:
    def test_username_min_length(self):
        with pytest.raises(ValidationError):
            UserCreate(username="ab", password="pass1234", role_id=1)

    def test_password_min_length(self):
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", password="ab", role_id=1)


class TestSaleConstraints:
    def test_empty_items_rejected(self):
        with pytest.raises(ValidationError):
            SaleCreate(items=[])

    def test_quantity_min_one(self):
        with pytest.raises(ValidationError):
            SaleCreate(items=[SaleItemCreate(product_id=1, quantity=0)])


class TestLayawayConstraints:
    def test_deposit_must_be_positive(self):
        with pytest.raises(ValidationError):
            LayawayCreate(
                customer_id=1, deposit=Decimal("0"), items=[LayawayItemCreate(product_id=1, quantity=1)]
            )

    def test_empty_items_rejected(self):
        with pytest.raises(ValidationError):
            LayawayCreate(customer_id=1, deposit=Decimal("10.00"), items=[])


class TestPaymentConstraints:
    def test_amount_must_be_positive(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("0"))

    def test_amount_negative_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("-5.00"))


class TestLayawayItemAddConstraints:
    def test_valid_item_add(self):
        item = LayawayItemAdd(product_id=1, quantity=2)
        assert item.product_id == 1
        assert item.quantity == 2

    def test_quantity_below_one_rejected(self):
        with pytest.raises(ValidationError):
            LayawayItemAdd(product_id=1, quantity=0)

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValidationError):
            LayawayItemAdd(product_id=1, quantity=-1)


class TestLayawayItemUpdateConstraints:
    def test_valid_item_update(self):
        item = LayawayItemUpdate(quantity=3)
        assert item.quantity == 3

    def test_quantity_below_one_rejected(self):
        with pytest.raises(ValidationError):
            LayawayItemUpdate(quantity=0)

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValidationError):
            LayawayItemUpdate(quantity=-5)
