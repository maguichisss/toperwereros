from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, ChangePasswordRequest, ProfileUpdateRequest, UserCreate, UserResponse
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_permission,
)

router = APIRouter()


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not user.active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
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


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Contraseña actual incorrecta")
    if len(data.new_password) < 4:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 4 caracteres")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"ok": True, "detail": "Contraseña actualizada correctamente"}


@router.put("/profile")
def update_profile(
    data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.post("/avatar")
def upload_avatar(image: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE = 5 * 1024 * 1024
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Solo se permiten imágenes JPEG, PNG y WebP")
    import os, uuid
    ext = os.path.splitext(image.filename or "avatar.jpg")[1]
    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    path = os.path.join(uploads_dir, filename)
    content = image.file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Archivo demasiado grande (máx 5MB)")
    with open(path, "wb") as f:
        f.write(content)
    return {"image_url": f"/uploads/{filename}"}


@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_permission("user.manage"))):
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


@router.post("/register", status_code=201)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
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
