"""Tests for color CRUD and hex validation."""

from app.models import Color, Product
from decimal import Decimal


def _create_color(db, name="Red", hex_val="#FF0000"):
    color = Color(name=name, hex=hex_val)
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


class TestListColors:
    def test_empty_list(self, client, admin_headers):
        resp = client.get("/api/colors", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_with_data(self, client, admin_headers, db):
        _create_color(db, "Red", "#FF0000")
        _create_color(db, "Blue", "#0000FF")
        resp = client.get("/api/colors", headers=admin_headers)
        assert len(resp.json()) == 2


class TestCreateColor:
    def test_create_success(self, client, admin_headers):
        resp = client.post("/api/colors", json={"name": "Green", "hex": "#00FF00"}, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["hex"] == "#00FF00"

    def test_create_invalid_hex(self, client, admin_headers):
        resp = client.post("/api/colors", json={"name": "Bad", "hex": "not-hex"}, headers=admin_headers)
        assert resp.status_code == 400

    def test_create_duplicate_name(self, client, admin_headers, db):
        _create_color(db, "Dup", "#111111")
        resp = client.post("/api/colors", json={"name": "Dup", "hex": "#222222"}, headers=admin_headers)
        assert resp.status_code == 409


class TestUpdateColor:
    def test_update_success(self, client, admin_headers, db):
        c = _create_color(db)
        resp = client.put(f"/api/colors/{c.id}", json={"name": "Blue", "hex": "#0000FF"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Blue"

    def test_update_not_found(self, client, admin_headers):
        resp = client.put("/api/colors/9999", json={"name": "X", "hex": "#000000"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_invalid_hex(self, client, admin_headers, db):
        c = _create_color(db)
        resp = client.put(f"/api/colors/{c.id}", json={"name": "X", "hex": "bad"}, headers=admin_headers)
        assert resp.status_code == 400


class TestDeleteColor:
    def test_delete_success(self, client, admin_headers, db):
        c = _create_color(db)
        resp = client.delete(f"/api/colors/{c.id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_delete_in_use(self, client, admin_headers, db):
        c = _create_color(db)
        product = Product(name="P", code="P1", price=Decimal("10.00"), colors=[c])
        db.add(product)
        db.commit()
        resp = client.delete(f"/api/colors/{c.id}", headers=admin_headers)
        assert resp.status_code == 409

    def test_delete_not_found(self, client, admin_headers):
        resp = client.delete("/api/colors/9999", headers=admin_headers)
        assert resp.status_code == 404


class TestEmployeeColorAccess:
    def test_employee_can_list_colors(self, client, employee_headers, db):
        _create_color(db)
        resp = client.get("/api/colors", headers=employee_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_employee_cannot_create_color(self, client, employee_headers):
        resp = client.post("/api/colors", json={"name": "Green", "hex": "#00FF00"}, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_update_color(self, client, employee_headers, db):
        c = _create_color(db)
        resp = client.put(f"/api/colors/{c.id}", json={"name": "X", "hex": "#000000"}, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_delete_color(self, client, employee_headers, db):
        c = _create_color(db)
        resp = client.delete(f"/api/colors/{c.id}", headers=employee_headers)
        assert resp.status_code == 403


class TestViewerColorAccess:
    def test_viewer_can_list_colors(self, client, viewer_headers, db):
        _create_color(db)
        resp = client.get("/api/colors", headers=viewer_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_viewer_cannot_create_color(self, client, viewer_headers):
        resp = client.post("/api/colors", json={"name": "X", "hex": "#000000"}, headers=viewer_headers)
        assert resp.status_code == 403
