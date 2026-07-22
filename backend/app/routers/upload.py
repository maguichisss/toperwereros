"""Image upload endpoints — validates magic bytes and saves to disk."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse

from app.models import User
from app.auth import require_permission

router = APIRouter()

UPLOAD_DIR: str = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b'\xff\xd8\xff': ('.jpg', 'image/jpeg'),
    b'\x89PNG\r\n\x1a\n': ('.png', 'image/png'),
    b'RIFF': ('.webp', 'image/webp'),
}

MAX_SIZE: int = 5 * 1024 * 1024


def detect_image_type(header: bytes) -> tuple[str, str] | None:
    """Detect image format from the first 12 bytes of file content.

    Checks the header against known magic bytes for JPEG, PNG, and WebP.

    Args:
        header: The first 12 bytes of the uploaded file.

    Returns:
        A tuple of ``(extension, mime_type)`` if detected, or ``None``.
    """

    for magic, (ext, mime) in MAGIC_BYTES.items():
        if header.startswith(magic):
            return ext, mime
    if header[:4] == b'RIFF':
        return '.webp', 'image/webp'
    return None


@router.post("", tags=["Upload"], summary="Upload image",
              description="Upload a product image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit. Returns the URL path; link to a product via PUT /api/products/{id}.")
def upload_image(
    image: UploadFile = File(...),
    current_user: User = Depends(require_permission("product.edit")),
) -> dict[str, str]:
    """Upload a product image to the local uploads directory.

    Validates that the file is ≤ 5 MB, has a recognized image header (JPEG,
    PNG, or WebP), and stores it with a random UUID filename.

    Args:
        image: The multipart file upload containing image bytes.
        current_user: Authenticated user with ``product.edit`` permission.

    Returns:
        JSON dict with ``image_url`` pointing to the saved file.

    Raises:
        HTTPException: 400 if file is too small, too large, or not a
            supported image format.
    """

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
