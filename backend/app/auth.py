"""Authentication and authorization utilities.

Provides JWT token creation and verification, password hashing with bcrypt,
role-based permission checking, and FastAPI dependencies for extracting the
current authenticated user from requests.
"""

import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["*"],
    "employee": [
        "product.view", "product.create", "product.edit", "product.delete",
        "sale.view", "sale.create",
        "apartado.view", "apartado.create", "apartado.edit",
        "customer.view", "customer.create", "customer.edit", "customer.delete",
        "category.view", "color.view",
    ],
    "viewer": [
        "product.view", "sale.view", "apartado.view",
        "customer.view", "category.view", "color.view",
    ],
}


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt-hashed password string.
    """

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The password to verify.
        hashed_password: The stored bcrypt hash to compare against.

    Returns:
        True if the password matches, False otherwise.
    """

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed JWT access token with an expiration claim.

    The ``sub`` claim is converted to a string for JWT compliance.

    Args:
        data: Payload dictionary to encode; must contain ``sub`` (user ID).

    Returns:
        Encoded JWT string.
    """

    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that extracts and validates the current user from the JWT.

    Decodes the Bearer token, looks up the user in the database, and verifies
    the account is active.

    Args:
        credentials: Bearer token from the Authorization header.
        db: Database session.

    Raises:
        HTTPException: 401 if no credentials, invalid token, or user not found/inactive.

    Returns:
        The authenticated User ORM instance.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return user


def require_permission(*perms: str) -> Callable[..., Awaitable[User]]:
    """Return a FastAPI dependency that checks the user has the required permission(s).

    Admin role (wildcard ``*``) bypasses all checks. For other roles, the user
    must have at least one of the specified permissions or a wildcard parent
    permission (e.g. ``product.*`` covers ``product.view``).

    Args:
        *perms: One or more permission strings required to access the endpoint.

    Returns:
        A dependency callable that yields the authorized User or raises 403.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        """Check that the current user's role holds the required permissions."""
        role_perms = ROLE_PERMISSIONS.get(current_user.role.name, [])
        if "*" in role_perms:
            return current_user
        for perm in perms:
            if perm in role_perms:
                return current_user
            if any(p.endswith(".*") and perm.startswith(p[:-1]) for p in role_perms):
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para realizar esta acción",
        )
    return dependency
