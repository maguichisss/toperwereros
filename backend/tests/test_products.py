"""Tests for product CRUD, search, pagination, and validation."""

from decimal import Decimal

from app.models import Product, Category, Color


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


def _create_product(db, name="Widget", code="W001", price="19.99", stock=10, category_ids=None, color_ids=None):
    product = Product(name=name, code=code, price=Decimal(price), stock=stock)
    if category_ids:
        cats = db.query(Category).filter(Category.id.in_(category_ids)).all()
        product.categories = cats
    if color_ids:
        cols = db.query(Color).filter(Color.id.in_(color_ids)).all()
        product.colors = cols
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


class TestListProducts:
    def test_empty_list(self, client, admin_headers):
        resp = client.get("/api/products", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_products(self, client, admin_headers, db):
        _create_product(db)
        resp = client.get("/api/products", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_by_name(self, client, admin_headers, db):
        _create_product(db, name="Alpha Widget", code="AW01")
        _create_product(db, name="Beta Gadget", code="BG01")
        resp = client.get("/api/products?q=Alpha", headers=admin_headers)
        assert resp.json()["total"] == 1
        assert resp.json()["products"][0]["name"] == "Alpha Widget"

    def test_search_by_code(self, client, admin_headers, db):
        _create_product(db, name="Widget", code="XYZ123")
        resp = client.get("/api/products?q=XYZ", headers=admin_headers)
        assert resp.json()["total"] == 1

    def test_pagination(self, client, admin_headers, db):
        for i in range(5):
            _create_product(db, name=f"P{i}", code=f"C{i}")
        resp = client.get("/api/products?page=1&per_page=2", headers=admin_headers)
        data = resp.json()
        assert data["total"] == 5
        assert len(data["products"]) == 2

    def test_category_filter(self, client, admin_headers, db):
        cat = _create_category(db, "Tools")
        _create_product(db, name="Hammer", code="H01", category_ids=[cat.id])
        _create_product(db, name="Book", code="B01")
        resp = client.get(f"/api/products?category_ids={cat.id}", headers=admin_headers)
        assert resp.json()["total"] == 1

    def test_stock_zero_products_excluded_from_stock_filter(self, client, admin_headers, db):
        _create_product(db, name="InStock", code="IS01", stock=5)
        _create_product(db, name="OutOfStock", code="OS01", stock=0)
        resp = client.get("/api/products", headers=admin_headers)
        assert resp.json()["total"] == 2


class TestGetProduct:
    def test_get_existing(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.get(f"/api/products/{p.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == "W001"

    def test_get_not_found(self, client, admin_headers):
        resp = client.get("/api/products/9999", headers=admin_headers)
        assert resp.status_code == 404


class TestCreateProduct:
    def test_create_success(self, client, admin_headers, db):
        resp = client.post(
            "/api/products",
            json={"name": "New", "code": "N01", "price": "25.00", "stock": 3},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "New"

    def test_create_with_categories(self, client, admin_headers, db):
        cat = _create_category(db)
        resp = client.post(
            "/api/products",
            json={"name": "New", "code": "N02", "price": "10.00", "categoryIds": [cat.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert len(resp.json()["categories"]) == 1

    def test_create_duplicate_code(self, client, admin_headers, db):
        _create_product(db, code="DUP01")
        resp = client.post(
            "/api/products",
            json={"name": "Other", "code": "DUP01", "price": "5.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_empty_name(self, client, admin_headers):
        resp = client.post(
            "/api/products",
            json={"name": "", "code": "X01", "price": "5.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestUpdateProduct:
    def test_update_success(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.put(
            f"/api/products/{p.id}",
            json={"name": "Updated", "code": "W001", "price": "29.99", "stock": 8},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_not_found(self, client, admin_headers):
        resp = client.put(
            "/api/products/9999",
            json={"name": "X", "code": "X", "price": "1.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestDeleteProduct:
    def test_delete_success(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.delete(f"/api/products/{p.id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_delete_not_found(self, client, admin_headers):
        resp = client.delete("/api/products/9999", headers=admin_headers)
        assert resp.status_code == 404
