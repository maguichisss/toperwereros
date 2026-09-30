"""Tests for auth middleware: JWT validation, wildcard permissions, inactive users."""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
import jwt

from app.auth import JWT_SECRET as APP_JWT_SECRET, create_access_token, ROLE_PERMISSIONS
from app.main import app
from app.models import User, Role


JWT_SECRET = "dev-secret-change-in-production"
ALGORITHM = "HS256"


def _legacy_style_token(secret: str) -> str:
    """Build an HS256 token with stdlib only, as python-jose would.

    Independent of any JWT library: header/payload/signature are assembled by
    hand, so the test proves tokens minted before the python-jose -> PyJWT
    migration still validate against the app (JWT_SECRET, decode, exp check).
    """

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(
        json.dumps(
            {"sub": "999999", "iat": 1759000000, "exp": 4070908800},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    signature = b64(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


class TestLegacyTokenFormat:
    def test_pre_migration_token_still_validates(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {_legacy_style_token(APP_JWT_SECRET)}"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "User not found or inactive"


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
