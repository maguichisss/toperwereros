"""Tests for category CRUD and in-use guard."""

from app.models import Category, Product
from decimal import Decimal


def _create_category(db, name="Electronics"):
    cat = Category(name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


class TestListCategories:
    def test_empty_list(self, client, admin_headers):
        resp = client.get("/api/categories", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_with_data(self, client, admin_headers, db):
        _create_category(db, "A")
        _create_category(db, "B")
        resp = client.get("/api/categories", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "A"


class TestCreateCategory:
    def test_create_success(self, client, admin_headers):
        resp = client.post("/api/categories", json={"name": "New Cat"}, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Cat"

    def test_create_duplicate(self, client, admin_headers, db):
        _create_category(db, "Dup")
        resp = client.post("/api/categories", json={"name": "Dup"}, headers=admin_headers)
        assert resp.status_code == 409

    def test_create_empty_name(self, client, admin_headers):
        resp = client.post("/api/categories", json={"name": ""}, headers=admin_headers)
        assert resp.status_code == 422


class TestUpdateCategory:
    def test_update_success(self, client, admin_headers, db):
        cat = _create_category(db, "Old")
        resp = client.put(f"/api/categories/{cat.id}", json={"name": "New"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_update_not_found(self, client, admin_headers):
        resp = client.put("/api/categories/9999", json={"name": "X"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_duplicate_name(self, client, admin_headers, db):
        cat1 = _create_category(db, "A")
        _create_category(db, "B")
        resp = client.put(f"/api/categories/{cat1.id}", json={"name": "B"}, headers=admin_headers)
        assert resp.status_code == 409


class TestDeleteCategory:
    def test_delete_success(self, client, admin_headers, db):
        cat = _create_category(db)
        resp = client.delete(f"/api/categories/{cat.id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_delete_in_use(self, client, admin_headers, db):
        cat = _create_category(db)
        product = Product(name="P", code="P1", price=Decimal("10.00"), categories=[cat])
        db.add(product)
        db.commit()
        resp = client.delete(f"/api/categories/{cat.id}", headers=admin_headers)
        assert resp.status_code == 409

    def test_delete_not_found(self, client, admin_headers):
        resp = client.delete("/api/categories/9999", headers=admin_headers)
        assert resp.status_code == 404


class TestEmployeeCategoryAccess:
    def test_employee_can_list_categories(self, client, employee_headers, db):
        _create_category(db)
        resp = client.get("/api/categories", headers=employee_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_employee_cannot_create_category(self, client, employee_headers):
        resp = client.post("/api/categories", json={"name": "New"}, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_update_category(self, client, employee_headers, db):
        cat = _create_category(db)
        resp = client.put(f"/api/categories/{cat.id}", json={"name": "X"}, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_delete_category(self, client, employee_headers, db):
        cat = _create_category(db)
        resp = client.delete(f"/api/categories/{cat.id}", headers=employee_headers)
        assert resp.status_code == 403


class TestViewerCategoryAccess:
    def test_viewer_can_list_categories(self, client, viewer_headers, db):
        _create_category(db)
        resp = client.get("/api/categories", headers=viewer_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_viewer_cannot_create_category(self, client, viewer_headers):
        resp = client.post("/api/categories", json={"name": "New"}, headers=viewer_headers)
        assert resp.status_code == 403
