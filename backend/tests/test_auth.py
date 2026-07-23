"""Tests for authentication, JWT, user management, and profile endpoints."""

from decimal import Decimal

from app.models import User, Role


class TestLogin:
    def test_login_success(self, client, admin_user, admin_headers):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db, _roles):
        from app.auth import hash_password
        user = User(
            username="inactive",
            hashed_password=hash_password("x"),
            active=False,
            role_id=_roles["admin"].id,
        )
        db.add(user)
        db.commit()
        resp = client.post("/api/auth/login", json={"username": "inactive", "password": "x"})
        assert resp.status_code == 401


class TestMe:
    def test_me_returns_profile(self, client, admin_user, admin_headers):
        resp = client.get("/api/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role_name"] == "admin"

    def test_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "newpass123"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_change_password_wrong_current(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong", "new_password": "newpass123"},
            headers=admin_headers,
        )
        assert resp.status_code == 400


class TestRegister:
    def test_register_success(self, client, admin_headers, db, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pass1234", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_register_duplicate_username(self, client, admin_user, admin_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "pass1234", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_register_no_permission(self, client, employee_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pass1234", "role_id": _roles["employee"].id},
            headers=employee_headers,
        )
        assert resp.status_code == 403


class TestListUsers:
    def test_list_users(self, client, admin_user, admin_headers):
        resp = client.get("/api/auth/users", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_users_no_permission(self, client, employee_headers):
        resp = client.get("/api/auth/users", headers=employee_headers)
        assert resp.status_code == 403


class TestUpdateProfile:
    def test_update_email(self, client, admin_user, admin_headers):
        resp = client.put(
            "/api/auth/profile",
            json={"email": "new@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@test.com"

    def test_update_duplicate_email(self, client, admin_user, employee_user, admin_headers):
        resp = client.put(
            "/api/auth/profile",
            json={"email": "employee@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 400
