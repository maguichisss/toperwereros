"""Tests for layaway CRUD, payments, cancel, and complete."""

from decimal import Decimal
from unittest.mock import patch

from app.models import Product, Customer


def _create_product(db, name="Widget", code="W001", price="100.00", stock=10):
    product = Product(name=name, code=code, price=Decimal(price), stock=stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_customer(db, name="Jane Doe"):
    cust = Customer(name=name, phone="555-0001")
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


def _create_layaway(client, admin_headers, db, deposit="30.00", product_price="100.00", quantity=1):
    p = _create_product(db, price=product_price)
    c = _create_customer(db)
    resp = client.post(
        "/api/layaways",
        json={
            "customer_id": c.id,
            "deposit": deposit,
            "items": [{"product_id": p.id, "quantity": quantity}],
        },
        headers=admin_headers,
    )
    return resp, p, c


class TestCreateLayaway:
    def test_create_success(self, client, admin_headers, db):
        resp, p, c = _create_layaway(client, admin_headers, db)
        assert resp.status_code == 201
        data = resp.json()
        assert Decimal(data["total"]) == Decimal("100.00")
        assert Decimal(data["deposit"]) == Decimal("30.00")
        assert Decimal(data["balance"]) == Decimal("70.00")
        assert data["status"] == "active"
        assert len(data["items"]) == 1
        assert len(data["payments"]) == 1

    def test_create_with_notes(self, client, admin_headers, db):
        p = _create_product(db)
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
                "notes": "Cliente pagará en dos abonos",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["notes"] == "Cliente pagará en dos abonos"

    def test_update_notes_success(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.patch(
            f"/api/layaways/{layaway_id}",
            json={"notes": "Notas actualizadas"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Notas actualizadas"

    def test_update_notes_not_active(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        resp = client.patch(
            f"/api/layaways/{layaway_id}",
            json={"notes": "Nope"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_update_notes_not_found(self, client, admin_headers):
        resp = client.patch(
            "/api/layaways/9999",
            json={"notes": "Nope"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_update_notes_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.patch(
                f"/api/layaways/{layaway_id}",
                json={"notes": "Falla"},
                headers=admin_headers,
            )
            assert resp.status_code == 500

    def test_create_stock_decremented(self, client, admin_headers, db):
        _create_layaway(client, admin_headers, db)
        # Refresh product from DB
        p = db.query(Product).filter(Product.code == "W001").first()
        assert p.stock == 9

    def test_create_insufficient_stock(self, client, admin_headers, db):
        p = _create_product(db, stock=2)
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "50.00",
                "items": [{"product_id": p.id, "quantity": 5}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_deposit_exceeds_total(self, client, admin_headers, db):
        p = _create_product(db, price="50.00")
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "100.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_no_customer(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/layaways",
            json={"deposit": "10.00", "items": [{"product_id": p.id, "quantity": 1}]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_inline_customer(self, client, admin_headers, db):
        p = _create_product(db, price="50.00")
        resp = client.post(
            "/api/layaways",
            json={
                "customer": {"name": "New Person", "phone": "555-9999"},
                "deposit": "20.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["customer_name"] == "New Person"

    def test_create_layaway_fails_when_commit_fails(self, client, admin_headers, db):
        p = _create_product(db)
        c = _create_customer(db)
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                "/api/layaways",
                json={
                    "customer_id": c.id,
                    "deposit": "30.00",
                    "items": [{"product_id": p.id, "quantity": 1}],
                },
                headers=admin_headers,
            )
            assert resp.status_code == 500

    def test_create_both_customer_id_and_customer(self, client, admin_headers, db):
        p = _create_product(db)
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "customer": {"name": "X", "phone": "0"},
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_nonexistent_customer_id(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": 9999,
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestAddPayment:
    def test_add_payment_success(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "30.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert Decimal(resp.json()["balance"]) == Decimal("40.00")

    def test_add_payment_completes_layaway(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        resp = client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "70.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "completed"
        assert resp.json()["sale_id"] is not None
        assert resp.json()["balance"] == "0.00"
        assert [p["amount"] for p in resp.json()["payments"]] == ["30.00", "70.00"]

    def test_add_payment_overpayment_rejected(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        resp = client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "100.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_add_payment_not_found(self, client, admin_headers):
        resp = client.post("/api/layaways/9999/payments", json={"amount": "10.00"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_add_payment_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                f"/api/layaways/{layaway_id}/payments",
                json={"amount": "50.00"},
                headers=admin_headers,
            )
            assert resp.status_code == 500

    def test_payment_to_cancelled_layaway(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        client.patch(f"/api/layaways/{layaway_id}/cancel", headers=admin_headers)
        resp = client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "10.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 400


class TestCancelLayaway:
    def test_cancel_success(self, client, admin_headers, db):
        layaway_resp, p, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.patch(f"/api/layaways/{layaway_id}/cancel", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
        db.refresh(p)
        assert p.stock == 10

    def test_cancel_not_active(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="100.00")
        layaway_id = layaway_resp.json()["id"]
        client.patch(f"/api/layaways/{layaway_id}/cancel", headers=admin_headers)
        resp = client.patch(f"/api/layaways/{layaway_id}/cancel", headers=admin_headers)
        assert resp.status_code == 400

    def test_cancel_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.patch(f"/api/layaways/{layaway_id}/cancel", headers=admin_headers)
            assert resp.status_code == 500

    def test_cancel_nonexistent_layaway(self, client, admin_headers):
        resp = client.patch("/api/layaways/9999/cancel", headers=admin_headers)
        assert resp.status_code == 404


class TestCompleteLayaway:
    def test_complete_success(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["sale_id"] is not None

    def test_complete_records_remaining_abono(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        assert layaway_resp.json()["balance"] == "70.00"
        resp = client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["sale_id"] is not None
        assert body["balance"] == "0.00"
        payments = body["payments"]
        assert [p["amount"] for p in payments] == ["30.00", "70.00"]

    def test_complete_not_active(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        resp = client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        assert resp.status_code == 400

    def test_complete_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
            assert resp.status_code == 500

    def test_complete_nonexistent_layaway(self, client, admin_headers):
        resp = client.patch("/api/layaways/9999/complete", headers=admin_headers)
        assert resp.status_code == 404


class TestListLayaways:
    def test_list_layaways(self, client, admin_headers, db):
        _create_layaway(client, admin_headers, db)
        resp = client.get("/api/layaways", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_layaway(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == layaway_id

    def test_get_layaway_not_found(self, client, admin_headers):
        resp = client.get("/api/layaways/9999", headers=admin_headers)
        assert resp.status_code == 404

    def test_list_filter_by_status(self, client, admin_headers, db):
        _create_layaway(client, admin_headers, db)
        resp = client.get("/api/layaways?status=active", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_customer_id(self, client, admin_headers, db):
        _, _, c = _create_layaway(client, admin_headers, db)
        resp = client.get(f"/api/layaways?customer_id={c.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_no_match(self, client, admin_headers, db):
        _create_layaway(client, admin_headers, db)
        resp = client.get("/api/layaways?status=cancelled", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestEmployeeLayawayAccess:
    def test_employee_can_create_layaway(self, client, employee_headers, db):
        p = _create_product(db)
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=employee_headers,
        )
        assert resp.status_code == 201

    def test_employee_can_list_layaways(self, client, employee_headers, db):
        _create_layaway(client, employee_headers, db)
        resp = client.get("/api/layaways", headers=employee_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_employee_can_get_layaway(self, client, employee_headers, db):
        layaway_resp, _, _ = _create_layaway(client, employee_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.get(f"/api/layaways/{layaway_id}", headers=employee_headers)
        assert resp.status_code == 200


class TestViewerLayawayAccess:
    def test_viewer_can_list_layaways(self, client, admin_headers, viewer_headers, db):
        _create_layaway(client, admin_headers, db)
        resp = client.get("/api/layaways", headers=viewer_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_viewer_cannot_create_layaway(self, client, viewer_headers, db):
        p = _create_product(db)
        c = _create_customer(db)
        resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=viewer_headers,
        )
        assert resp.status_code == 403


class TestAddLayawayItem:
    def test_add_item_success(self, client, admin_headers, db):
        layaway_resp, p1, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        resp = client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 2},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["items"]) == 2
        assert Decimal(data["total"]) == Decimal("200.00")
        assert Decimal(data["balance"]) == Decimal("170.00")

    def test_add_item_stock_decremented(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 2},
            headers=admin_headers,
        )
        db.refresh(p2)
        assert p2.stock == 3

    def test_add_item_insufficient_stock(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=1)
        resp = client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 5},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_add_item_product_not_found(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": 9999, "quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_add_item_not_active(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="100.00")
        layaway_id = layaway_resp.json()["id"]
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00")
        client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        resp = client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_add_item_layaway_not_found(self, client, admin_headers, db):
        p = _create_product(db)
        resp = client.post(
            "/api/layaways/9999/items",
            json={"product_id": p.id, "quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_add_item_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        p2 = _create_product(db, name="Gadget", code="G001")
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                f"/api/layaways/{layaway_id}/items",
                json={"product_id": p2.id, "quantity": 2},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestRemoveLayawayItem:
    def test_remove_item_success(self, client, admin_headers, db):
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        layaway_resp, p1, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 2},
            headers=admin_headers,
        )
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_to_remove = layaway_data["items"][1]["id"]
        resp = client.delete(
            f"/api/layaways/{layaway_id}/items/{item_to_remove}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert Decimal(data["total"]) == Decimal("100.00")
        assert Decimal(data["balance"]) == Decimal("70.00")

    def test_remove_item_stock_restored(self, client, admin_headers, db):
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 2},
            headers=admin_headers,
        )
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_to_remove = layaway_data["items"][1]["id"]
        client.delete(f"/api/layaways/{layaway_id}/items/{item_to_remove}", headers=admin_headers)
        db.refresh(p2)
        assert p2.stock == 5

    def test_remove_last_item_rejected(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.delete(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_remove_item_total_below_payments(self, client, admin_headers, db):
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 1},
            headers=admin_headers,
        )
        client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "80.00"},
            headers=admin_headers,
        )
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_to_remove = layaway_data["items"][0]["id"]
        resp = client.delete(
            f"/api/layaways/{layaway_id}/items/{item_to_remove}",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_remove_item_not_found(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.delete(
            f"/api/layaways/{layaway_id}/items/9999",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_remove_item_not_active(self, client, admin_headers, db):
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="100.00")
        layaway_id = layaway_resp.json()["id"]
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 1},
            headers=admin_headers,
        )
        client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.delete(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_remove_item_fails_when_commit_fails(self, client, admin_headers, db):
        p2 = _create_product(db, name="Gadget", code="G001", price="50.00", stock=5)
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        client.post(
            f"/api/layaways/{layaway_id}/items",
            json={"product_id": p2.id, "quantity": 2},
            headers=admin_headers,
        )
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.delete(
                f"/api/layaways/{layaway_id}/items/{item_id}",
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestUpdateLayawayItem:
    def test_increase_quantity_success(self, client, admin_headers, db):
        layaway_resp, p, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 3},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["quantity"] == 3
        assert Decimal(data["total"]) == Decimal("300.00")
        assert Decimal(data["balance"]) == Decimal("270.00")

    def test_increase_stock_decremented(self, client, admin_headers, db):
        layaway_resp, p, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 3},
            headers=admin_headers,
        )
        db.refresh(p)
        assert p.stock == 7

    def test_increase_insufficient_stock(self, client, admin_headers, db):
        p = _create_product(db, stock=3)
        c = _create_customer(db)
        layaway_resp = client.post(
            "/api/layaways",
            json={
                "customer_id": c.id,
                "deposit": "30.00",
                "items": [{"product_id": p.id, "quantity": 1}],
            },
            headers=admin_headers,
        )
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 10},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_decrease_quantity_success(self, client, admin_headers, db):
        layaway_resp, p, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 3},
            headers=admin_headers,
        )
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["quantity"] == 1
        assert Decimal(data["total"]) == Decimal("100.00")
        assert Decimal(data["balance"]) == Decimal("70.00")

    def test_decrease_stock_restored(self, client, admin_headers, db):
        layaway_resp, p, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 3},
            headers=admin_headers,
        )
        client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 1},
            headers=admin_headers,
        )
        db.refresh(p)
        assert p.stock == 9

    def test_same_quantity_noop(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["quantity"] == 1

    def test_decrease_total_below_payments(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 3},
            headers=admin_headers,
        )
        client.post(
            f"/api/layaways/{layaway_id}/payments",
            json={"amount": "80.00"},
            headers=admin_headers,
        )
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_update_item_not_found(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db)
        layaway_id = layaway_resp.json()["id"]
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/9999",
            json={"quantity": 5},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_update_item_not_active(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="100.00")
        layaway_id = layaway_resp.json()["id"]
        client.patch(f"/api/layaways/{layaway_id}/complete", headers=admin_headers)
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        resp = client.put(
            f"/api/layaways/{layaway_id}/items/{item_id}",
            json={"quantity": 5},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_update_item_fails_when_commit_fails(self, client, admin_headers, db):
        layaway_resp, _, _ = _create_layaway(client, admin_headers, db, deposit="30.00")
        layaway_id = layaway_resp.json()["id"]
        layaway_data = client.get(f"/api/layaways/{layaway_id}", headers=admin_headers).json()
        item_id = layaway_data["items"][0]["id"]
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.put(
                f"/api/layaways/{layaway_id}/items/{item_id}",
                json={"quantity": 5},
                headers=admin_headers,
            )
            assert resp.status_code == 500
