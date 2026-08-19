"""Shared test fixtures for the Store Catalog API test suite.

Provides an isolated SQLite in-memory database per test, FastAPI TestClient,
and pre-built admin/employee user fixtures with valid JWT tokens.
"""

import io
import os
from decimal import Decimal

os.environ.setdefault("JWT_SECRET", "test-secret-for-testing")

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.auth import hash_password, create_access_token

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    """Enable foreign key support in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    """Yield a test database session and roll back after the request."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _setup_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clear rate limiter state between tests so limits don't carry over
    app.state.limiter._storage.reset()
    from app.routers import auth as auth_router, upload as upload_router
    auth_router.limiter._storage.reset()
    upload_router.limiter._storage.reset()


@pytest.fixture()
def db() -> Session:
    """Yield a raw database session for direct ORM operations in tests."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def _roles(db: Session) -> dict[str, Role]:
    """Insert admin, employee, and viewer roles and return them by name."""
    roles = {}
    for name in ("admin", "employee", "viewer"):
        role = Role(name=name)
        db.add(role)
        db.flush()
        roles[name] = role
    db.commit()
    return roles


@pytest.fixture()
def admin_user(db: Session, _roles: dict[str, Role]) -> User:
    """Create an admin user and return the ORM object."""
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        active=True,
        role_id=_roles["admin"].id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def employee_user(db: Session, _roles: dict[str, Role]) -> User:
    """Create an employee user and return the ORM object."""
    user = User(
        username="employee",
        email="employee@test.com",
        hashed_password=hash_password("emp123"),
        active=True,
        role_id=_roles["employee"].id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def viewer_user(db: Session, _roles: dict[str, Role]) -> User:
    """Create a viewer user and return the ORM object."""
    user = User(
        username="viewer",
        email="viewer@test.com",
        hashed_password=hash_password("view123"),
        active=True,
        role_id=_roles["viewer"].id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def admin_token(admin_user: User) -> str:
    """Return a valid JWT token for the admin user."""
    return create_access_token({"sub": admin_user.id})


@pytest.fixture()
def employee_token(employee_user: User) -> str:
    """Return a valid JWT token for the employee user."""
    return create_access_token({"sub": employee_user.id})


@pytest.fixture()
def viewer_token(viewer_user: User) -> str:
    """Return a valid JWT token for the viewer user."""
    return create_access_token({"sub": viewer_user.id})


@pytest.fixture()
def admin_headers(admin_token: str) -> dict[str, str]:
    """Return Authorization headers for the admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def employee_headers(employee_token: str) -> dict[str, str]:
    """Return Authorization headers for the employee user."""
    return {"Authorization": f"Bearer {employee_token}"}


@pytest.fixture()
def viewer_headers(viewer_token: str) -> dict[str, str]:
    """Return Authorization headers for the viewer user."""
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture()
def client() -> TestClient:
    """Return a FastAPI TestClient wired to the test database."""
    return TestClient(app)


def _make_image_bytes(fmt: str = "png") -> bytes:
    """Return minimal valid image bytes for the given format."""
    if fmt == "png":
        # PNG signature
        return (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    elif fmt == "jpg":
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100
    elif fmt == "webp":
        return b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50
    return b"\x00" * 20


def _make_png_upload(filename: str = "test.png") -> UploadFile:
    """Return a FastAPI UploadFile containing a minimal PNG."""
    content = _make_image_bytes("png")
    return UploadFile(filename=filename, file=io.BytesIO(content))
