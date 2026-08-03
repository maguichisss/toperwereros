"""Tests for config helpers: detect_image_type, safe_upload_path, escape_like."""

import pytest
from fastapi import HTTPException

from app.config import detect_image_type, escape_like, safe_upload_path


class TestDetectImageType:
    def test_png(self):
        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert detect_image_type(header) == (".png", "image/png")

    def test_jpg(self):
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert detect_image_type(header) == (".jpg", "image/jpeg")

    def test_webp(self):
        header = b"RIFF\x00\x00\x00\x00WEBP"
        assert detect_image_type(header) == (".webp", "image/webp")

    def test_unknown(self):
        header = b"\x00\x00\x00\x00" + b"\x00" * 8
        assert detect_image_type(header) is None


class TestSafeUploadPath:
    def test_none_returns_none(self):
        assert safe_upload_path(None) is None

    def test_empty_returns_none(self):
        assert safe_upload_path("") is None

    def test_valid_filename(self, tmp_path):
        import os
        from app import config
        old_dir = config.UPLOAD_DIR
        config.UPLOAD_DIR = str(tmp_path)
        try:
            (tmp_path / "photo.png").touch()
            result = safe_upload_path("/uploads/photo.png")
            assert result == os.path.join(str(tmp_path), "photo.png")
        finally:
            config.UPLOAD_DIR = old_dir

    def test_path_traversal_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            safe_upload_path("/uploads/../../../etc/passwd")
        assert exc_info.value.status_code == 400


class TestEscapeLike:
    def test_percent_escaped(self):
        assert escape_like("100%") == "100\\%"

    def test_underscore_escaped(self):
        assert escape_like("hello_world") == "hello\\_world"

    def test_backslash_escaped(self):
        assert escape_like("path\\file") == "path\\\\file"

    def test_all_special_chars(self):
        assert escape_like("%_\\") == "\\%\\_\\\\"

    def test_no_special_chars(self):
        assert escape_like("hello world") == "hello world"
