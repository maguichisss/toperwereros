"""Tests for customer CRUD and search."""

from unittest.mock import patch

from app.models import Customer


def _create_customer(db, name="John Doe", phone="555-1234"):
    cust = Customer(name=name, phone=phone)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


class TestListCustomers:
    def test_empty_list(self, client, admin_headers):
        resp = client.get("/api/customers", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_with_data(self, client, admin_headers, db):
        _create_customer(db, "Alice", "555-0001")
        _create_customer(db, "Bob", "555-0002")
        resp = client.get("/api/customers", headers=admin_headers)
        assert len(resp.json()) == 2

    def test_search_by_name(self, client, admin_headers, db):
        _create_customer(db, "Alice Smith", "555-0001")
        _create_customer(db, "Bob Jones", "555-0002")
        resp = client.get("/api/customers?q=Alice", headers=admin_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Alice Smith"

    def test_search_by_phone(self, client, admin_headers, db):
        _create_customer(db, "Alice", "555-1234")
        _create_customer(db, "Bob", "555-5678")
        resp = client.get("/api/customers?q=1234", headers=admin_headers)
        assert len(resp.json()) == 1


class TestGetCustomer:
    def test_get_existing(self, client, admin_headers, db):
        c = _create_customer(db)
        resp = client.get(f"/api/customers/{c.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "John Doe"

    def test_get_not_found(self, client, admin_headers):
        resp = client.get("/api/customers/9999", headers=admin_headers)
        assert resp.status_code == 404


class TestCreateCustomer:
    def test_create_success(self, client, admin_headers):
        resp = client.post(
            "/api/customers",
            json={"name": "New Person", "phone": "555-9999"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Person"

    def test_create_customer_fails_when_commit_fails(self, client, admin_headers):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                "/api/customers",
                json={"name": "New Person", "phone": "555-9999"},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestUpdateCustomer:
    def test_update_success(self, client, admin_headers, db):
        c = _create_customer(db)
        resp = client.put(
            f"/api/customers/{c.id}",
            json={"name": "Updated Name", "phone": "555-0000"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_update_not_found(self, client, admin_headers):
        resp = client.put(
            "/api/customers/9999",
            json={"name": "X", "phone": "0"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_update_customer_fails_when_commit_fails(self, client, admin_headers, db):
        c = _create_customer(db)
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.put(
                f"/api/customers/{c.id}",
                json={"name": "Updated", "phone": "555-0000"},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestDeleteCustomer:
    def test_delete_success(self, client, admin_headers, db):
        c = _create_customer(db)
        resp = client.delete(f"/api/customers/{c.id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_delete_not_found(self, client, admin_headers):
        resp = client.delete("/api/customers/9999", headers=admin_headers)
        assert resp.status_code == 404

    def test_delete_customer_fails_when_commit_fails(self, client, admin_headers, db):
        c = _create_customer(db)
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.delete(f"/api/customers/{c.id}", headers=admin_headers)
            assert resp.status_code == 500


class TestEmployeeCustomerAccess:
    def test_employee_can_list_customers(self, client, employee_headers, db):
        _create_customer(db)
        resp = client.get("/api/customers", headers=employee_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_employee_can_create_customer(self, client, employee_headers):
        resp = client.post(
            "/api/customers",
            json={"name": "Emp Customer", "phone": "555-0000"},
            headers=employee_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Emp Customer"

    def test_employee_can_update_customer(self, client, employee_headers, db):
        c = _create_customer(db)
        resp = client.put(
            f"/api/customers/{c.id}",
            json={"name": "Updated", "phone": "1"},
            headers=employee_headers,
        )
        assert resp.status_code == 200

    def test_employee_can_delete_customer(self, client, employee_headers, db):
        c = _create_customer(db)
        resp = client.delete(f"/api/customers/{c.id}", headers=employee_headers)
        assert resp.status_code == 204


class TestViewerCustomerAccess:
    def test_viewer_can_list_customers(self, client, viewer_headers, db):
        _create_customer(db)
        resp = client.get("/api/customers", headers=viewer_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_viewer_cannot_create_customer(self, client, viewer_headers):
        resp = client.post(
            "/api/customers",
            json={"name": "X", "phone": "0"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_viewer_cannot_update_customer(self, client, viewer_headers, db):
        c = _create_customer(db)
        resp = client.put(
            f"/api/customers/{c.id}",
            json={"name": "Y", "phone": "1"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_viewer_cannot_delete_customer(self, client, viewer_headers, db):
        c = _create_customer(db)
        resp = client.delete(f"/api/customers/{c.id}", headers=viewer_headers)
        assert resp.status_code == 403
