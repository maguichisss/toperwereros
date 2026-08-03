"""Tests for sales creation, stock validation, and listing."""

from decimal import Decimal
from unittest.mock import patch

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

    def test_sale_fails_when_commit_fails(self, client, admin_headers, db):
        """Verify the endpoint calls db.commit() by mocking it to raise."""
        p = _create_product(db, stock=5)

        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                "/api/sales",
                json={"items": [{"product_id": p.id, "quantity": 2}]},
                headers=admin_headers,
            )
            assert resp.status_code == 500


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


class TestSaleCreatedBy:
    def test_created_by_tracks_user(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["created_by_name"] == "admin"


class TestMultiItemSale:
    def test_multi_item_sale(self, client, admin_headers, db):
        p1 = _create_product(db, name="W1", code="W01", price="10.00", stock=5)
        p2 = _create_product(db, name="W2", code="W02", price="20.00", stock=5)
        resp = client.post(
            "/api/sales",
            json={"items": [
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 1},
            ]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert Decimal(resp.json()["total"]) == Decimal("40.00")
        assert len(resp.json()["items"]) == 2


class TestEmployeeSaleAccess:
    def test_employee_can_create_sale(self, client, employee_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=employee_headers,
        )
        assert resp.status_code == 201

    def test_employee_can_list_sales(self, client, employee_headers, db):
        p = _create_product(db)
        client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=employee_headers,
        )
        resp = client.get("/api/sales", headers=employee_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestViewerSaleAccess:
    def test_viewer_can_list_sales(self, client, viewer_headers):
        resp = client.get("/api/sales", headers=viewer_headers)
        assert resp.status_code == 200

    def test_viewer_cannot_create_sale(self, client, viewer_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/sales",
            json={"items": [{"product_id": p.id, "quantity": 1}]},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_list_sales_pagination(self, client, admin_headers, db):
        for i in range(3):
            p = _create_product(db, name=f"P{i}", code=f"C{i:03d}", stock=10)
            client.post(
                "/api/sales",
                json={"items": [{"product_id": p.id, "quantity": 1}]},
                headers=admin_headers,
            )
        resp = client.get("/api/sales?page=1&per_page=2", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
