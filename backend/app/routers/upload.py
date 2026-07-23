"""Image upload endpoints — validates magic bytes and saves to disk."""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import UPLOAD_DIR, MAX_SIZE, detect_image_type
from app.models import User
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("", tags=["Upload"], summary="Upload image",
              description="Upload a product image. Validates magic bytes (JPEG/PNG/WebP) and enforces a 5 MB size limit. Returns the URL path; link to a product via PUT /api/products/{id}. Rate-limited to 5 attempts per minute per IP.")
@limiter.limit("5/minute")
def upload_image(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(require_permission("product.edit")),
) -> dict[str, str]:
    """Upload a product image to the local uploads directory.

    Validates that the file is ≤ 5 MB, has a recognized image header (JPEG,
    PNG, or WebP), and stores it with a random UUID filename.
    Rate-limited to 5 attempts per minute per IP.

    Args:
        request: The raw HTTP request (used by slowapi for rate limiting).
        image: The multipart file upload containing image bytes.
        current_user: Authenticated user with ``product.edit`` permission.

    Returns:
        JSON dict with ``image_url`` pointing to the saved file.

    Raises:
        HTTPException: 400 if file is too small, too large, or not a
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
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(path, "wb") as f:
            f.write(content)
    except OSError:
        logger.exception("Failed to write upload file")
        raise HTTPException(500, "Error al subir la imagen")
    return {"image_url": f"/uploads/{filename}"}
