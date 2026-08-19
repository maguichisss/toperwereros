"""Tests for authentication, JWT, user management, and profile endpoints."""

import io
import os
from decimal import Decimal
from unittest.mock import patch

from fastapi import UploadFile

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


class TestUploadAvatar:
    def _make_png_upload(self):
        content = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return UploadFile(filename="avatar.png", file=io.BytesIO(content))

    def _make_jpg_upload(self):
        content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        return UploadFile(filename="avatar.jpg", file=io.BytesIO(content))

    def test_upload_avatar_success(self, client, admin_headers):
        resp = client.post(
            "/api/auth/avatar",
            files={"image": ("avatar.png", self._make_png_upload().file, "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["image_url"].startswith("/uploads/avatar_")

    def test_upload_avatar_jpg(self, client, admin_headers):
        resp = client.post(
            "/api/auth/avatar",
            files={"image": ("avatar.jpg", self._make_jpg_upload().file, "image/jpeg")},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["image_url"].endswith(".jpg")

    def test_upload_avatar_invalid_magic(self, client, admin_headers):
        resp = client.post(
            "/api/auth/avatar",
            files={"image": ("bad.bin", io.BytesIO(b"\x00" * 20), "application/octet-stream")},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_upload_avatar_too_small(self, client, admin_headers):
        resp = client.post(
            "/api/auth/avatar",
            files={"image": ("tiny.bin", io.BytesIO(b"\x89PNG"), "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_upload_avatar_old_deleted(self, client, admin_headers, db):
        from app.auth import hash_password
        user = db.query(User).filter(User.username == "admin").first()
        user.image_url = "/uploads/avatar_old.png"
        db.commit()

        resp1 = client.post(
            "/api/auth/avatar",
            files={"image": ("a.png", self._make_png_upload().file, "image/png")},
            headers=admin_headers,
        )
        assert resp1.status_code == 200
        old_path = os.path.join(os.getcwd(), "uploads", "avatar_old.png")
        assert not os.path.exists(old_path)

    def test_upload_avatar_no_auth(self, client):
        resp = client.post(
            "/api/auth/avatar",
            files={"image": ("a.png", io.BytesIO(b"\x89PNG"), "image/png")},
        )
        assert resp.status_code in (401, 403)


class TestChangePassword:
    def test_change_password_success(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "newpass123456"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_change_password_wrong_current(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong", "new_password": "newpass123456"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_change_password_too_short(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "ab"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_change_password_fails_when_commit_fails(self, client, admin_user, admin_headers):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                "/api/auth/change-password",
                json={"current_password": "admin123", "new_password": "newpass123456"},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestRegister:
    def test_register_success(self, client, admin_headers, db, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pass12345678", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_register_duplicate_username(self, client, admin_user, admin_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "pass12345678", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_register_duplicate_email(self, client, admin_user, admin_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "unique", "password": "pass12345678", "email": "admin@test.com", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_register_no_permission(self, client, employee_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pass12345678", "role_id": _roles["employee"].id},
            headers=employee_headers,
        )
        assert resp.status_code == 403

    def test_register_fails_when_commit_fails(self, client, admin_headers, _roles):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.post(
                "/api/auth/register",
                json={"username": "newuser", "password": "pass12345678", "role_id": _roles["employee"].id},
                headers=admin_headers,
            )
            assert resp.status_code == 500


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
        resp = client.patch(
            "/api/auth/profile",
            json={"email": "new@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@test.com"

    def test_update_duplicate_email(self, client, admin_user, employee_user, admin_headers):
        resp = client.patch(
            "/api/auth/profile",
            json={"email": "employee@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_partial_update_preserves_other_fields(self, client, admin_user, admin_headers):
        resp = client.patch(
            "/api/auth/profile",
            json={"email": "partial@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "partial@test.com"
        assert data["username"] == "admin"

    def test_empty_body_noop(self, client, admin_user, admin_headers):
        resp = client.patch(
            "/api/auth/profile",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@test.com"

    def test_update_profile_fails_when_commit_fails(self, client, admin_user, admin_headers):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.patch(
                "/api/auth/profile",
                json={"email": "updated@test.com"},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestUpdateUser:
    def test_update_user_success(self, client, admin_headers, employee_user, _roles):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"email": "new@test.com", "role_id": _roles["viewer"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["role_id"] == _roles["viewer"].id

    def test_update_user_username(self, client, admin_headers, employee_user):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"username": " NewName "},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    def test_update_user_password(self, client, admin_headers, employee_user):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"password": "newpass123456"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        login = client.post(
            "/api/auth/login",
            json={"username": "employee", "password": "newpass123456"},
        )
        assert login.status_code == 200

    def test_update_user_not_found(self, client, admin_headers):
        resp = client.put("/api/auth/users/9999", json={}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_user_duplicate_username(self, client, admin_headers, employee_user):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"username": "admin"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_update_user_duplicate_email(self, client, admin_headers, employee_user):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"email": "admin@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_update_user_no_permission(self, client, employee_headers, employee_user):
        resp = client.put(
            f"/api/auth/users/{employee_user.id}",
            json={"email": "x@test.com"},
            headers=employee_headers,
        )
        assert resp.status_code == 403

    def test_update_user_fails_when_commit_fails(self, client, admin_headers, employee_user):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.put(
                f"/api/auth/users/{employee_user.id}",
                json={"email": "x@test.com"},
                headers=admin_headers,
            )
            assert resp.status_code == 500


class TestLoginLockout:
    def _reset_limiter(self):
        from app.routers.auth import limiter
        limiter._storage.reset()

    def test_failed_attempts_increment(self, client, admin_user):
        self._reset_limiter()
        for i in range(4):
            resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
            assert resp.status_code == 401

    def test_locks_after_max_attempts(self, client, admin_user, db):
        self._reset_limiter()
        for i in range(5):
            resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
            assert resp.status_code == 401
        db.expire_all()
        user = db.query(User).filter(User.username == "admin").first()
        assert user.locked_until is not None
        assert user.failed_login_attempts == 5

    def test_locked_account_rejects_correct_password(self, client, admin_user, db):
        self._reset_limiter()
        for i in range(5):
            client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        self._reset_limiter()
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 401

    def test_successful_login_resets_counter(self, client, admin_user, db):
        self._reset_limiter()
        for i in range(4):
            client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        self._reset_limiter()
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        db.expire_all()
        user = db.query(User).filter(User.username == "admin").first()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestPasswordValidation:
    def test_change_password_too_short(self, client, admin_user, admin_headers):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "short"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_register_password_too_short(self, client, admin_headers, _roles):
        resp = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "short", "role_id": _roles["employee"].id},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestToggleUserActive:
    def test_deactivate_user_success(self, client, admin_headers, employee_user):
        resp = client.patch(
            f"/api/auth/users/{employee_user.id}/active",
            json={"active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_activate_user_success(self, client, admin_headers, employee_user, db):
        employee_user.active = False
        db.commit()
        resp = client.patch(
            f"/api/auth/users/{employee_user.id}/active",
            json={"active": True},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    def test_deactivate_self_forbidden(self, client, admin_user, admin_headers):
        resp = client.patch(
            f"/api/auth/users/{admin_user.id}/active",
            json={"active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_toggle_active_no_permission(self, client, employee_headers, employee_user):
        resp = client.patch(
            f"/api/auth/users/{employee_user.id}/active",
            json={"active": False},
            headers=employee_headers,
        )
        assert resp.status_code == 403

    def test_toggle_active_fails_when_commit_fails(self, client, admin_headers, employee_user):
        def raise_on_commit(self):
            raise RuntimeError("Simulated commit failure")

        with patch("sqlalchemy.orm.Session.commit", raise_on_commit):
            resp = client.patch(
                f"/api/auth/users/{employee_user.id}/active",
                json={"active": False},
                headers=admin_headers,
            )
            assert resp.status_code == 500
