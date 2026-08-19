"""Authentication, user management, avatar upload, and profile endpoints."""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter

from app.config import UPLOAD_DIR, MAX_SIZE, detect_image_type, safe_upload_path, GCS_BUCKET, get_forwarded_ip, LOCKOUT_MAX_ATTEMPTS, LOCKOUT_DURATION_MINUTES
from app.database import get_db
from app.models import User, Role
from app.schemas import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    ProfileUpdateRequest,
    RoleCreate,
    RoleResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_permission,
)

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_forwarded_ip)


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

    user = db.query(User).filter(User.username == data.username.strip().lower()).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    if not user.active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    if not verify_password(data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= LOCKOUT_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        db.commit()
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)


@router.get("/roles", response_model=list[RoleResponse], tags=["Auth"], summary="List roles",
              description="Return all roles. Requires admin (user.manage) permission.")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> list[RoleResponse]:
    """Return all roles ordered by id. Requires ``user.manage`` permission.

    Args:
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        List of RoleResponse objects.
    """

    roles = db.query(Role).order_by(Role.id).all()
    return [RoleResponse(id=r.id, name=r.name) for r in roles]


@router.post("/roles", response_model=RoleResponse, status_code=201, tags=["Auth"], summary="Create role",
              description="Create a new role. Requires admin (user.manage) permission.")
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> RoleResponse:
    """Create a new role. Requires ``user.manage`` permission.

    Args:
        data: Role creation payload (name).
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        The newly created RoleResponse.

    Raises:
        HTTPException: 400 if role name already exists.
    """

    name = data.name.strip().lower()
    existing = db.query(Role).filter(Role.name == name).first()
    if existing:
        raise HTTPException(400, "El nombre del rol ya existe")
    role = Role(name=name)
    db.add(role)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create role")
        raise HTTPException(500, "Error al crear el rol")
    db.refresh(role)
    return RoleResponse(id=role.id, name=role.name)


@router.get("/me", response_model=UserResponse, tags=["Auth"], summary="Get current user",
              description="Return the authenticated user's profile including id, username, email, role, and avatar.")
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile.

    Args:
        current_user: Authenticated user injected by dependency.

    Returns:
        UserResponse with id, username, email, role, and avatar info.

    Raises:
        HTTPException: 401 if the token is invalid or the user is not found.
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
              description="Change the authenticated user's password. New password must be at least 4 characters. Rate-limited to 1 attempt per minute per IP.")
@limiter.limit("1/minute")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | bool]:
    """Change the authenticated user's password.

    Rate-limited to 1 attempt per minute per IP.

    Args:
        request: The raw HTTP request (used by slowapi for rate limiting).
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
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to change password for user %d", current_user.id)
        raise HTTPException(500, "Error al cambiar la contraseña")
    return {"ok": True, "detail": "Contraseña actualizada correctamente"}


@router.patch("/profile", response_model=UserResponse, tags=["Auth"], summary="Update profile",
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
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update profile for user %d", current_user.id)
        raise HTTPException(500, "Error al actualizar el perfil")
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
              description="Upload a profile avatar image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit. Rate-limited to 3 attempts per minute per IP.")
@limiter.limit("3/minute")
def upload_avatar(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Upload a profile avatar image for the authenticated user.

    Validates magic bytes (JPEG, PNG, WebP) and enforces a 5 MB size limit.
    Rate-limited to 3 attempts per minute per IP.

    Args:
        request: The raw HTTP request (used by slowapi for rate limiting).
        image: Multipart file upload containing the avatar image.
        current_user: Authenticated user injected by dependency.

    Returns:
        ``{"image_url": "/uploads/avatar_<uuid>.<ext>"}``.

    Raises:
        HTTPException: 400 if the file is too small, too large, or not a
            supported image format.
    """

    chunks = []
    total = 0
    while True:
        chunk = image.file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_SIZE:
            raise HTTPException(400, "Archivo demasiado grande (máx 5MB)")
        chunks.append(chunk)
    content = b"".join(chunks)
    if len(content) < 8:
        raise HTTPException(400, "Archivo de imagen inválido")
    result = detect_image_type(content[:12])
    if not result:
        raise HTTPException(400, "Solo se permiten imágenes JPEG, PNG y WebP")
    ext, expected_mime = result
    if current_user.image_url:
        if GCS_BUCKET:
            from app.gcs import delete_from_gcs
            delete_from_gcs(current_user.image_url)
        else:
            old_path = safe_upload_path(current_user.image_url)
            if old_path and os.path.exists(old_path):
                os.remove(old_path)
    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    try:
        if GCS_BUCKET:
            from app.gcs import upload_to_gcs
            upload_to_gcs(content, filename)
        else:
            path = os.path.join(UPLOAD_DIR, filename)
            with open(path, "wb") as f:
                f.write(content)
    except Exception:
        logger.exception("Failed to upload avatar")
        raise HTTPException(500, "Error al subir el avatar")
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

    Raises:
        HTTPException: 403 if the user lacks ``user.manage`` permission.
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
              description="Create a new user account. Username and email must be unique. Requires admin (user.manage) permission. Rate-limited to 5 attempts per minute per IP.")
@limiter.limit("5/minute")
def register(
    request: Request,
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Register a new user account. Requires ``user.manage`` permission.

    Rate-limited to 5 attempts per minute per IP.

    Args:
        request: The raw HTTP request (used by slowapi for rate limiting).
        data: User creation payload (username, password, email, role_id).
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        The newly created UserResponse.

    Raises:
        HTTPException: 400 if username or email already exists.
    """

    username = data.username.strip().lower()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(400, "El nombre de usuario ya existe")
    if data.email:
        existing_email = db.query(User).filter(User.email == data.email).first()
        if existing_email:
            raise HTTPException(400, "El email ya está registrado")
    user = User(
        username=username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role_id=data.role_id,
        active=True,
    )
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to register user")
        raise HTTPException(500, "Error al registrar el usuario")
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


@router.put("/users/{user_id}", response_model=UserResponse, tags=["Auth"], summary="Update user",
            description="Admin-only. Update username, email, role, password, or active status of a user.")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Update an existing user's fields.

    Args:
        user_id: ID of the user to update.
        data: Partial update payload (username, email, role_id, password, active).
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        The updated UserResponse.

    Raises:
        HTTPException: 404 if user not found.
        HTTPException: 400 if username/email already exists, or safety guard violated.
        HTTPException: 500 if database commit fails.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    if data.username is not None:
        username = data.username.strip().lower()
        existing = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing:
            raise HTTPException(400, "El nombre de usuario ya existe")
        user.username = username

    if data.email is not None:
        existing_email = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if existing_email:
            raise HTTPException(400, "El email ya está registrado")
        user.email = data.email

    if data.role_id is not None:
        if user_id == current_user.id:
            raise HTTPException(400, "No puedes cambiar tu propio rol")
        user.role_id = data.role_id

    if data.active is not None:
        if user_id == current_user.id and not data.active:
            raise HTTPException(400, "No puedes desactivar tu propia cuenta")
        user.active = data.active

    if data.password is not None:
        user.hashed_password = hash_password(data.password)

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update user %d", user_id)
        raise HTTPException(500, "Error al actualizar el usuario")
    db.refresh(user)
    logger.info("User %d updated by admin %d", user_id, current_user.id)
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


@router.patch("/users/{user_id}/active", response_model=UserResponse, tags=["Auth"],
              summary="Toggle user active status",
              description="Enable or disable a user account. Admin only. Cannot deactivate yourself.")
def toggle_user_active(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Toggle a user's active/disabled status.

    Args:
        user_id: ID of the user to toggle.
        data: Dictionary with ``active`` boolean field.
        db: Active database session.
        current_user: Authenticated user with ``user.manage`` permission.

    Returns:
        The updated UserResponse.

    Raises:
        HTTPException: 404 if user not found.
        HTTPException: 400 if trying to deactivate yourself.
        HTTPException: 500 if database commit fails.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    active = data.get("active")
    if active is None:
        raise HTTPException(400, "El campo 'active' es requerido")

    if user_id == current_user.id and not active:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta")

    user.active = active
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to toggle active status for user %d", user_id)
        raise HTTPException(500, "Error al actualizar el estado del usuario")
    db.refresh(user)
    action = "activated" if active else "deactivated"
    logger.info("User %d %s by admin %d", user_id, action, current_user.id)
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
