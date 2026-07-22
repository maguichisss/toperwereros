import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.models import User
from app.auth import require_permission

router = APIRouter()

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAGIC_BYTES = {
    b'\xff\xd8\xff': ('.jpg', 'image/jpeg'),
    b'\x89PNG\r\n\x1a\n': ('.png', 'image/png'),
    b'RIFF': ('.webp', 'image/webp'),
}

MAX_SIZE = 5 * 1024 * 1024


def detect_image_type(header: bytes) -> tuple[str, str] | None:
    for magic, (ext, mime) in MAGIC_BYTES.items():
        if header.startswith(magic):
            return ext, mime
    if header[:4] == b'RIFF':
        return '.webp', 'image/webp'
    return None


@router.post("")
def upload_image(image: UploadFile = File(...), current_user: User = Depends(require_permission("product.edit"))):
    content = image.file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File too large (max 5MB)")
    if len(content) < 8:
        raise HTTPException(400, "Archivo de imagen inválido")
    result = detect_image_type(content[:12])
    if not result:
        raise HTTPException(400, "Solo se permiten imágenes JPEG, PNG y WebP")
    ext, expected_mime = result
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return {"image_url": f"/uploads/{filename}"}
