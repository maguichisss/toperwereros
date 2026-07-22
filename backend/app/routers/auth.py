"""Authentication, user management, avatar upload, and profile endpoints."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    ProfileUpdateRequest,
    UserCreate,
    UserResponse,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_permission,
)

MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b'\xff\xd8\xff': ('.jpg', 'image/jpeg'),
    b'\x89PNG\r\n\x1a\n': ('.png', 'image/png'),
    b'RIFF': ('.webp', 'image/webp'),
}

MAX_SIZE: int = 5 * 1024 * 1024


def detect_image_type(header: bytes) -> tuple[str, str] | None:
    """Detect image format from the first 12 bytes of file content.

    Args:
        header: The first 12 bytes of the uploaded file.

    Returns:
        A tuple of ``(extension, mime_type)`` if detected, or ``None``.
    """

    for magic, (ext, mime) in MAGIC_BYTES.items():
        if header.startswith(magic):
            return ext, mime
    return None


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse, tags=["Auth"], summary="Login",
              description="Authenticate with username/password and receive a JWT token. Rate-limited to 5 attempts per minute per IP.")
@limiter.limit("5/minute")
def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Rate-limited to 5 attempts per minute per IP.

    Args:
        request: The raw HTTP request (used by slowapi for rate limiting).
        data: Login credentials (username and password).
        db: Active database session.

    Returns:
        TokenResponse containing the JWT ``access_token``.

    Raises:
        HTTPException: 401 if credentials are invalid or the user is inactive.
    """

    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not user.active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse, tags=["Auth"], summary="Get current user",
              description="Return the authenticated user's profile including id, username, email, role, and avatar.")
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile.

    Args:
        current_user: Authenticated user injected by dependency.

    Returns:
        UserResponse with id, username, email, role, and avatar info.
    """

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        image_url=current_user.image_url,
        active=current_user.active,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        created_at=current_user.created_at,
    )


@router.post("/change-password", tags=["Auth"], summary="Change password",
              description="Change the authenticated user's password. New password must be at least 4 characters.")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Change the authenticated user's password.

    Args:
        data: Current and new password.
        db: Active database session.
        current_user: Authenticated user injected by dependency.

    Returns:
        ``{"ok": True, "detail": "Contraseña actualizada correctamente"}``.

    Raises:
        HTTPException: 400 if the current password is incorrect or the new
            password is shorter than 4 characters.
    """

    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Contraseña actual incorrecta")
    if len(data.new_password) < 4:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 4 caracteres")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"ok": True, "detail": "Contraseña actualizada correctamente"}


@router.put("/profile", response_model=UserResponse, tags=["Auth"], summary="Update profile",
              description="Update own email and/or avatar URL. Email uniqueness is enforced across users.")
def update_profile(
    data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Update the authenticated user's email and/or avatar URL.

    Args:
        data: Profile update payload (email, image_url).
        db: Active database session.
        current_user: Authenticated user injected by dependency.

    Returns:
        Updated UserResponse.

    Raises:
        HTTPException: 400 if the new email is already taken by another user.
    """

    if data.email is not None:
        if data.email != current_user.email:
            existing = db.query(User).filter(User.email == data.email, User.id != current_user.id).first()
            if existing:
                raise HTTPException(400, "El email ya está registrado por otro usuario")
        current_user.email = data.email or None
    if data.image_url is not None:
        current_user.image_url = data.image_url
    db.commit()
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        image_url=current_user.image_url,
        active=current_user.active,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        created_at=current_user.created_at,
    )


@router.post("/avatar", tags=["Auth"], summary="Upload avatar",
              description="Upload a profile avatar image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit.")
def upload_avatar(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Upload a profile avatar image for the authenticated user.

    Validates magic bytes (JPEG, PNG, WebP) and enforces a 5 MB size limit.

    Args:
        image: Multipart file upload containing the avatar image.
        current_user: Authenticated user injected by dependency.

    Returns:
        ``{"image_url": "/uploads/avatar_<uuid>.<ext>"}``.

    Raises:
        HTTPException: 400 if the file is too small, too large, or not a
            supported image format.
    """

    content = image.file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Archivo demasiado grande (máx 5MB)")
    if len(content) < 8:
        raise HTTPException(400, "Archivo de imagen inválido")
    result = detect_image_type(content[:12])
    if not result:
        raise HTTPException(400, "Solo se permiten imágenes JPEG, PNG y WebP")
    ext, expected_mime = result
    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    path = os.path.join(uploads_dir, filename)
    with open(path, "wb") as f:
        f.write(content)
    return {"image_url": f"/uploads/{filename}"}


@router.get("/users", response_model=list[UserResponse], tags=["Auth"], summary="List users",
              description="Return all users ordered by username. Requires admin (user.manage) permission.")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> list[UserResponse]:
    """Return all users ordered by username. Requires ``user.manage`` permission.

    Args:
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        List of UserResponse objects.
    """

    users = db.query(User).order_by(User.username).all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            image_url=u.image_url,
            active=u.active,
            role_id=u.role_id,
            role_name=u.role.name if u.role else None,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/register", response_model=UserResponse, status_code=201, tags=["Auth"], summary="Register user",
              description="Create a new user account. Username and email must be unique. Requires admin (user.manage) permission.")
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Register a new user account. Requires ``user.manage`` permission.

    Args:
        data: User creation payload (username, password, email, role_id).
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        The newly created UserResponse.

    Raises:
        HTTPException: 400 if username or email already exists.
    """

    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(400, "El nombre de usuario ya existe")
    if data.email:
        existing_email = db.query(User).filter(User.email == data.email).first()
        if existing_email:
            raise HTTPException(400, "El email ya está registrado")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role_id=data.role_id,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        image_url=user.image_url,
        active=user.active,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        created_at=user.created_at,
    )
