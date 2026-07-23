"""Tests for sales creation, stock validation, and listing."""

from decimal import Decimal

from app.models import Product


def _create_product(db, name="Widget", code="W001", price="19.99", stock=10):
    product = Product(name=name, code=code, price=Decimal(price), stock=stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


class TestCreateSale:
    def test_create_sale_success(self, client, admin_headers, db):
        p = _create_product(db, stock=5)
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 2}]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert Decimal(data["total"]) == Decimal("39.98")
        assert len(data["items"]) == 1

    def test_create_sale_stock_decremented(self, client, admin_headers, db):
        p = _create_product(db, stock=5)
        client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 3}]},
            headers=admin_headers,
        )
        db.refresh(p)
        assert p.stock == 2

    def test_create_sale_insufficient_stock(self, client, admin_headers, db):
        p = _create_product(db, stock=2)
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 5}]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_sale_product_not_found(self, client, admin_headers):
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": 9999, "quantity": 1}]},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_create_sale_empty_items(self, client, admin_headers):
        resp = client.post("/api/sales", json={"items": []}, headers=admin_headers)
        assert resp.status_code == 422


class TestListSales:
    def test_list_sales(self, client, admin_headers, db):
        p = _create_product(db)
        client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=admin_headers,
        )
        resp = client.get("/api/sales", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_sale(self, client, admin_headers, db):
        p = _create_product(db)
        create_resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=admin_headers,
        )
        sale_id = create_resp.json()["id"]
        resp = client.get(f"/api/sales/{sale_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == sale_id

    def test_get_sale_not_found(self, client, admin_headers):
        resp = client.get("/api/sales/9999", headers=admin_headers)
        assert resp.status_code == 404
