"""Tests for auth middleware: JWT validation, wildcard permissions, inactive users."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.auth import create_access_token, ROLE_PERMISSIONS
from app.main import app
from app.models import User, Role


JWT_SECRET = "dev-secret-change-in-production"
ALGORITHM = "HS256"


class TestExpiredToken:
    def test_expired_token_returns_401(self, client, admin_user):
        payload = {"sub": str(admin_user.id), "exp": datetime.now(timezone.utc) - timedelta(hours=1)}
        token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestMalformedToken:
    def test_garbage_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert resp.status_code == 401

    def test_empty_bearer_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401


class TestMissingSubClaim:
    def test_no_sub_claim_returns_401(self, client):
        payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestWildcardPermission:
    def test_admin_wildcard_bypasses_all(self, client, admin_user, admin_headers):
        resp = client.get("/api/auth/users", headers=admin_headers)
        assert resp.status_code == 200

    def test_product_wildcard_covers_view(self, client, db, _roles):
        employee = User(
            username="wildcardemp",
            hashed_password="x",
            active=True,
            role_id=_roles["employee"].id,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        token = create_access_token({"sub": employee.id})
        resp = client.get("/api/products", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestInactiveUser:
    def test_inactive_user_returns_401(self, client, db, _roles):
        user = User(
            username="inactive",
            hashed_password="x",
            active=False,
            role_id=_roles["admin"].id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token({"sub": user.id})
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
