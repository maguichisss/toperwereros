"""Tests for the shared query DSL (operators, pagination, projection).

Covers the ``skip``/``limit`` / ``field__op=value`` / ``modo`` / ``campos``
behaviour on every list GET endpoint plus unit tests for the parser.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import Product, Category, Color, Customer, Sale, Layaway
from app.query_filters import (
    PRODUCT_FIELDS,
    SALE_FIELDS,
    apply_filters,
    end_of_day,
    parse_date_range,
    parse_day,
    parse_filters,
    parse_projection,
    project_rows,
    resolve_pagination,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _create_category(db, name="Electronics"):
    cat = Category(name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def _create_color(db, name="Red", hex_val="#FF0000"):
    color = Color(name=name, hex=hex_val)
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


def _create_product(db, name="Widget", code="W001", price="19.99", stock=10,
                    category_ids=None, color_ids=None, ubicacion=None, created_at=None):
    product = Product(
        name=name, code=code, price=Decimal(price), stock=stock, ubicacion=ubicacion
    )
    if category_ids:
        product.categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
    if color_ids:
        product.colors = db.query(Color).filter(Color.id.in_(color_ids)).all()
    db.add(product)
    db.commit()
    db.refresh(product)
    if created_at is not None:
        product.created_at = created_at
        db.commit()
        db.refresh(product)
    return product


def _ids(resp):
    return [p["id"] for p in resp.json()["products"]]


# ── Unit tests: parser ─────────────────────────────────────────────────────

class TestParseFilters:
    def test_plain_key_is_eq(self):
        parsed = parse_filters({"name": "Widget"}, PRODUCT_FIELDS)
        assert len(parsed) == 1
        assert parsed[0].op == "eq"
        assert parsed[0].value == "Widget"
        assert parsed[0].spec.key == "name"

    def test_operator_split(self):
        parsed = parse_filters({"price__gte": "50"}, PRODUCT_FIELDS)
        assert parsed[0].op == "gte"
        assert parsed[0].value == Decimal("50")

    def test_unknown_field_400(self):
        with pytest.raises(Exception) as exc:
            parse_filters({"precio__gte": "50"}, PRODUCT_FIELDS)
        assert exc.value.status_code == 400

    def test_invalid_int_400(self):
        with pytest.raises(Exception) as exc:
            parse_filters({"stock__gte": "abc"}, PRODUCT_FIELDS)
        assert exc.value.status_code == 400

    def test_like_on_numeric_400(self):
        with pytest.raises(Exception) as exc:
            parse_filters({"price__like": "19"}, PRODUCT_FIELDS)
        assert exc.value.status_code == 400

    def test_in_parses_csv(self):
        parsed = parse_filters({"id__in": "1,2,3"}, PRODUCT_FIELDS)
        assert parsed[0].op == "in"
        assert parsed[0].value == [1, 2, 3]

    def test_is_null_bool(self):
        parsed = parse_filters({"description__is_null": "true"}, PRODUCT_FIELDS)
        assert parsed[0].value is True

    def test_reserved_params_skipped(self):
        assert parse_filters(
            {"page": "1", "per_page": "20", "q": "x", "export": "true", "skip": "1"},
            PRODUCT_FIELDS,
        ) == []

    def test_created_date_coerces_to_start_of_day(self):
        parsed = parse_filters({"created_at__gte": "2026-03-01"}, PRODUCT_FIELDS)
        assert parsed[0].value == datetime(2026, 3, 1, 0, 0, 0)


class TestApplyFilters:
    def test_apply_relation_filter(self, db):
        cat = _create_category(db, "Tools")
        _create_product(db, name="Hammer", code="H01", category_ids=[cat.id])
        _create_product(db, name="Book", code="B01")
        query = db.query(Product)
        parsed = parse_filters({"category": "Tools"}, PRODUCT_FIELDS)
        result = apply_filters(query, parsed).all()
        assert [p.name for p in result] == ["Hammer"]

    def test_apply_in_and_ne(self, db):
        p1 = _create_product(db, name="A", code="A01", stock=3)
        p2 = _create_product(db, name="B", code="B02", stock=5)
        _create_product(db, name="C", code="C03", stock=9)
        query = db.query(Product)
        parsed = parse_filters({"stock__in": "3,5", "name__ne": "B"}, PRODUCT_FIELDS)
        result = apply_filters(query, parsed).all()
        assert [p.id for p in result] == [p1.id]


class TestProjection:
    def test_parse_basico(self):
        proj = parse_projection("basico", None, PRODUCT_FIELDS, ("id", "name"))
        assert proj is not None
        assert proj.keys == ("id", "name")

    def test_parse_campos(self):
        proj = parse_projection(None, "id,name", PRODUCT_FIELDS, ("id",))
        assert proj.keys == ("id", "name")

    def test_parse_campos_deduplicates(self):
        proj = parse_projection(None, "id,id,name", PRODUCT_FIELDS, ())
        assert proj.keys == ("id", "name")

    def test_bad_mode_400(self):
        with pytest.raises(Exception) as exc:
            parse_projection("completo", None, PRODUCT_FIELDS, ("id",))
        assert exc.value.status_code == 400

    def test_nonselectable_field_400(self):
        with pytest.raises(Exception) as exc:
            parse_projection(None, "category", PRODUCT_FIELDS, ())
        assert exc.value.status_code == 400

    def test_no_params_returns_none(self):
        assert parse_projection(None, None, PRODUCT_FIELDS, ("id",)) is None


class TestPagination:
    def test_explicit_skip_limit_wins(self):
        assert resolve_pagination(skip=2, limit=5, page=1, per_page=20) == (2, 5)

    def test_limit_only_starts_at_zero(self):
        assert resolve_pagination(skip=None, limit=5, page=1, per_page=20) == (0, 5)

    def test_legacy_page_per_page(self):
        assert resolve_pagination(skip=None, limit=None, page=3, per_page=20) == (40, 20)

    def test_export_disables_pagination(self):
        assert resolve_pagination(skip=2, limit=5, export=True) == (0, None)

    def test_not_default_paginated_returns_all(self):
        assert resolve_pagination(skip=None, limit=None, default_paginated=False) == (0, None)


class TestProjectRows:
    def test_converts_decimal(self, db):
        p = _create_product(db, name="X", price="12.50")
        proj = parse_projection(None, "id,name,price", PRODUCT_FIELDS, ())
        row = project_rows([p], proj)[0]
        assert row["price"] == 12.5
        assert row["name"] == "X"


class TestParseDateRange:
    def test_no_dates(self):
        assert parse_date_range(None, None) == (None, None)

    def test_start_only(self):
        start, end = parse_date_range("2024-05-01", None)
        assert start == datetime(2024, 5, 1, 0, 0, 0)
        assert end is None

    def test_end_only_is_inclusive(self):
        start, end = parse_date_range(None, "2024-05-01")
        assert start is None
        assert end == datetime(2024, 5, 2, 0, 0, 0)

    def test_both_dates(self):
        assert parse_date_range("2024-05-01", "2024-05-31") == (
            datetime(2024, 5, 1, 0, 0, 0),
            datetime(2024, 6, 1, 0, 0, 0),
        )

    def test_month_end_boundaries(self):
        assert parse_date_range("2024-01-31", "2024-02-29")[1] == datetime(2024, 3, 1)

    def test_invalid_start_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            parse_date_range("abc", None)
        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid date format. Use YYYY-MM-DD"

    def test_invalid_end_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            parse_date_range(None, "2024-13-45")
        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid date format. Use YYYY-MM-DD"

    def test_does_not_validate_ordering(self):
        start, end = parse_date_range("2024-05-31", "2024-05-01")
        assert start == datetime(2024, 5, 31)
        assert end == datetime(2024, 5, 2)

    def test_max_end_date_is_capped(self):
        assert parse_date_range(None, "9999-12-31") == (None, datetime.max)

    def test_max_both_dates_are_capped(self):
        assert parse_date_range("9999-12-31", "9999-12-31") == (
            datetime(9999, 12, 31),
            datetime.max,
        )

    def test_min_end_date_keeps_its_own_day(self):
        assert parse_date_range(None, "0001-01-01") == (
            None,
            datetime(1, 1, 2),
        )


class TestParseDay:
    def test_valid_date(self):
        assert parse_day("2024-05-01") == date(2024, 5, 1)

    def test_invalid_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            parse_day("abc")
        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid date format. Use YYYY-MM-DD"


class TestEndOfDay:
    def test_returns_midnight_of_next_day(self):
        assert end_of_day(date(2024, 5, 1)) == datetime(2024, 5, 2)

    def test_max_date_is_capped_instead_of_overflowing(self):
        assert end_of_day(date.max) == datetime.max

    def test_min_date_advances_normally(self):
        assert end_of_day(date.min) == datetime(1, 1, 2)


# ── Endpoint tests: products ───────────────────────────────────────────────

class TestProductsDSL:
    def test_price_range(self, client, admin_headers, db):
        _create_product(db, name="Cheap", code="C01", price="10.00")
        _create_product(db, name="Mid", code="M01", price="50.00")
        _create_product(db, name="Expensive", code="E01", price="120.00")
        resp = client.get(
            "/api/products?price__gte=40&price__lte=100", headers=admin_headers
        )
        assert [p["name"] for p in resp.json()["products"]] == ["Mid"]

    def test_contains_case_insensitive(self, client, admin_headers, db):
        _create_product(db, name="Cuervo Reposado", code="CR01")
        _create_product(db, name="Otra", code="OT01")
        resp = client.get("/api/products?name__contains=cuervo", headers=admin_headers)
        assert [p["name"] for p in resp.json()["products"]] == ["Cuervo Reposado"]

    def test_like_with_wildcards(self, client, admin_headers, db):
        _create_product(db, name="Tequila Jose Cuervo 750ml", code="T01")
        _create_product(db, name="Cerveza", code="CE01")
        resp = client.get(
            "/api/products?name__like=%25jose%25", headers=admin_headers
        )
        assert len(resp.json()["products"]) == 1

    def test_startswith_endswith(self, client, admin_headers, db):
        _create_product(db, name="Jose Cuervo", code="J01")
        _create_product(db, name="Don Julio", code="D01")
        resp = client.get("/api/products?name__startswith=jose", headers=admin_headers)
        assert len(resp.json()["products"]) == 1
        resp = client.get("/api/products?name__endswith=cuervo", headers=admin_headers)
        assert len(resp.json()["products"]) == 1

    def test_stock_lt(self, client, admin_headers, db):
        _create_product(db, name="Low", code="L01", stock=2)
        _create_product(db, name="High", code="H01", stock=10)
        resp = client.get("/api/products?stock__lt=5", headers=admin_headers)
        assert [p["name"] for p in resp.json()["products"]] == ["Low"]

    def test_id_in_and_not_in(self, client, admin_headers, db):
        p1 = _create_product(db, name="A", code="A01")
        p2 = _create_product(db, name="B", code="B02")
        p3 = _create_product(db, name="C", code="C03")
        resp = client.get(f"/api/products?id__in={p1.id},{p2.id}", headers=admin_headers)
        assert set(_ids(resp)) == {p1.id, p2.id}
        resp = client.get(
            f"/api/products?id__not_in={p3.id}", headers=admin_headers
        )
        assert set(_ids(resp)) == {p1.id, p2.id}

    def test_created_at_range(self, client, admin_headers, db):
        _create_product(db, name="Old", code="O01",
                        created_at=datetime(2026, 1, 1))
        _create_product(db, name="Middle", code="M01",
                        created_at=datetime(2026, 6, 15))
        _create_product(db, name="New", code="N01",
                        created_at=datetime(2026, 12, 1))
        resp = client.get(
            "/api/products?created_at__gte=2026-02-01&created_at__lt=2026-12-01",
            headers=admin_headers,
        )
        assert [p["name"] for p in resp.json()["products"]] == ["Middle"]

    def test_color_relation_filter(self, client, admin_headers, db):
        color = _create_color(db, "Rojo", "#FF0000")
        _create_product(db, name="Red", code="R01", color_ids=[color.id])
        _create_product(db, name="Blue", code="B01")
        resp = client.get("/api/products?color__contains=roj", headers=admin_headers)
        assert [p["name"] for p in resp.json()["products"]] == ["Red"]

    def test_combined_legacy_and_dsl(self, client, admin_headers, db):
        cat = _create_category(db, "Tools")
        color = _create_color(db, "Verde", "#00FF00")
        _create_product(db, name="Tornillo", code="T01", price="30.00",
                        category_ids=[cat.id], color_ids=[color.id], ubicacion="Caja 03")
        _create_product(db, name="Torre", code="T02", price="80.00",
                        category_ids=[cat.id], ubicacion="Caja 03")
        _create_product(db, name="Martillo", code="M01", price="30.00",
                        ubicacion="Estante")
        resp = client.get(
            "/api/products?category_ids=%d&price__lte=50&ubicacion__contains=caja"
            % cat.id,
            headers=admin_headers,
        )
        assert [p["name"] for p in resp.json()["products"]] == ["Tornillo"]

    def test_skip_limit_overrides_page(self, client, admin_headers, db):
        for i in range(5):
            _create_product(db, name=f"P{i}", code=f"C{i}")
        resp = client.get(
            "/api/products?skip=2&limit=1&page=1&per_page=3", headers=admin_headers
        )
        assert len(resp.json()["products"]) == 1

    def test_modo_basico(self, client, admin_headers, db):
        _create_product(db, name="Widget", code="W001")
        resp = client.get("/api/products?modo=basico", headers=admin_headers)
        data = resp.json()
        assert set(data.keys()) == {"products", "total"}
        assert set(data["products"][0].keys()) == {
            "id", "code", "name", "price", "stock", "ubicacion",
        }

    def test_campos(self, client, admin_headers, db):
        _create_product(db, name="Widget", code="W001")
        resp = client.get("/api/products?campos=id,name", headers=admin_headers)
        assert set(resp.json()["products"][0].keys()) == {"id", "name"}

    def test_modo_invalid_422(self, client, admin_headers):
        resp = client.get("/api/products?modo=completo", headers=admin_headers)
        assert resp.status_code == 422

    def test_unknown_param_400(self, client, admin_headers):
        resp = client.get("/api/products?precio__gte=1", headers=admin_headers)
        assert resp.status_code == 400

    def test_bad_campos_400(self, client, admin_headers):
        resp = client.get("/api/products?campos=id,noexiste", headers=admin_headers)
        assert resp.status_code == 400

    def test_bad_value_400(self, client, admin_headers):
        resp = client.get("/api/products?stock__gte=abc", headers=admin_headers)
        assert resp.status_code == 400


# ── Endpoint tests: other routers ──────────────────────────────────────────

class TestCustomersDSL:
    def test_name_contains(self, client, admin_headers, db):
        db.add(Customer(name="Alice", phone="111"))
        db.add(Customer(name="Bob", phone="222"))
        db.commit()
        resp = client.get("/api/customers?name__contains=lic", headers=admin_headers)
        assert [c["name"] for c in resp.json()["customers"]] == ["Alice"]

    def test_email_is_null(self, client, admin_headers, db):
        db.add(Customer(name="NoEmail"))
        db.add(Customer(name="HasEmail", email="a@b.com"))
        db.commit()
        resp = client.get(
            "/api/customers?email__is_null=true", headers=admin_headers
        )
        assert [c["name"] for c in resp.json()["customers"]] == ["NoEmail"]

    def test_no_pagination_by_default(self, client, admin_headers, db):
        for i in range(3):
            db.add(Customer(name=f"Customer{i}", phone=str(i)))
        db.commit()
        resp = client.get("/api/customers", headers=admin_headers)
        assert len(resp.json()["customers"]) == 3
        resp = client.get("/api/customers?limit=2", headers=admin_headers)
        assert len(resp.json()["customers"]) == 2
        assert resp.json()["total"] == 3


class TestSalesDSL:
    def test_total_gt(self, client, admin_headers, db):
        db.add(Sale(total=Decimal("100.00")))
        db.add(Sale(total=Decimal("250.00")))
        db.commit()
        resp = client.get("/api/sales?total__gt=150", headers=admin_headers)
        assert len(resp.json()["sales"]) == 1

    def test_created_after(self, client, admin_headers, db):
        sale = Sale(total=Decimal("50.00"), created_at=datetime(2026, 3, 1))
        db.add(sale)
        db.commit()
        resp = client.get(
            "/api/sales?created_at__gte=2026-01-01", headers=admin_headers
        )
        assert len(resp.json()["sales"]) == 1
        resp = client.get(
            "/api/sales?created_at__gte=2026-04-01", headers=admin_headers
        )
        assert resp.json()["sales"] == []


class TestLayawaysDSL:
    def _customer(self, db):
        c = Customer(name="Cliente Uno", phone="123")
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    def _layaway(self, db, customer, status="active", balance="80.00"):
        l = Layaway(
            customer_id=customer.id,
            total=Decimal("100.00"),
            deposit=Decimal("20.00"),
            balance=Decimal(balance),
            status=status,
        )
        db.add(l)
        db.commit()
        db.refresh(l)
        return l

    def test_status_in(self, client, admin_headers, db):
        c = self._customer(db)
        self._layaway(db, c, status="active")
        self._layaway(db, c, status="completed")
        resp = client.get(
            "/api/layaways?status__in=active,completed", headers=admin_headers
        )
        assert resp.json()["total"] == 2
        resp = client.get("/api/layaways?status=cancelled", headers=admin_headers)
        assert resp.json()["total"] == 0

    def test_balance_gte(self, client, admin_headers, db):
        c = self._customer(db)
        self._layaway(db, c, balance="80.00")
        self._layaway(db, c, balance="30.00")
        resp = client.get(
            "/api/layaways?balance__gte=50", headers=admin_headers
        )
        assert resp.json()["total"] == 1


class TestCategoriesColorsDSL:
    def test_category_name_like(self, client, admin_headers, db):
        _create_category(db, "Tequilas")
        _create_category(db, "Mezcales")
        resp = client.get(
            "/api/categories?name__startswith=tequi", headers=admin_headers
        )
        assert [c["name"] for c in resp.json()["categories"]] == ["Tequilas"]

    def test_color_hex_exact(self, client, admin_headers, db):
        _create_color(db, "Red", "#FF0000")
        _create_color(db, "Blue", "#0000FF")
        resp = client.get("/api/categories")  # touch categories route
        resp = client.get("/api/colors?hex=%23FF0000", headers=admin_headers)
        assert [c["name"] for c in resp.json()["colors"]] == ["Red"]