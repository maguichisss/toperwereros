"""Shared application constants and helpers."""

import os

from fastapi import HTTPException

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

    Args:
        header: The first 12 bytes of the uploaded file.

    Returns:
        A tuple of ``(extension, mime_type)`` if detected, or ``None``.
    """

    for magic, (ext, mime) in MAGIC_BYTES.items():
        if header.startswith(magic):
            return ext, mime
    return None


def safe_upload_path(url: str | None) -> str | None:
    """Resolve an image URL to an absolute path within UPLOAD_DIR.

    Validates that the resolved path cannot escape the uploads directory
    via ``..`` traversal.

    Args:
        url: An image URL like ``/uploads/<filename>``.

    Returns:
        The resolved absolute path, or ``None`` if *url* is empty.

    Raises:
        HTTPException: 400 if the path escapes UPLOAD_DIR.
    """

    if not url:
        return None
    filename = url.removeprefix("/uploads/")
    resolved = os.path.realpath(os.path.join(UPLOAD_DIR, filename))
    if not resolved.startswith(os.path.realpath(UPLOAD_DIR)):
        raise HTTPException(400, "Ruta de imagen inválida")
    return resolved


def escape_like(s: str) -> str:
    """Escape ``%``, ``_``, and ``\\`` for use in SQLAlchemy ``ilike()``.

    Args:
        s: The raw user input string.

    Returns:
        The escaped string safe for LIKE patterns.
    """

    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
