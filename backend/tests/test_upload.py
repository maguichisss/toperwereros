"""Tests for image upload — magic bytes, size limits, and chunked reads."""

import io

from fastapi import UploadFile


class TestUploadImage:
    def test_upload_png(self, client, admin_headers):
        from tests.conftest import _make_image_bytes
        content = _make_image_bytes("png")
        resp = client.post(
            "/api/upload",
            files={"image": ("test.png", io.BytesIO(content), "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["image_url"].startswith("/uploads/")

    def test_upload_jpg(self, client, admin_headers):
        from tests.conftest import _make_image_bytes
        content = _make_image_bytes("jpg")
        resp = client.post(
            "/api/upload",
            files={"image": ("test.jpg", io.BytesIO(content), "image/jpeg")},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_upload_invalid_magic_bytes(self, client, admin_headers):
        resp = client.post(
            "/api/upload",
            files={"image": ("test.bin", io.BytesIO(b"\x00\x00\x00\x00" * 10), "application/octet-stream")},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_upload_too_small(self, client, admin_headers):
        resp = client.post(
            "/api/upload",
            files={"image": ("tiny.png", io.BytesIO(b"\x89PNG"), "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_upload_no_auth(self, client):
        from tests.conftest import _make_image_bytes
        content = _make_image_bytes("png")
        resp = client.post(
            "/api/upload",
            files={"image": ("test.png", io.BytesIO(content), "image/png")},
        )
        assert resp.status_code == 401

    def test_upload_webp(self, client, admin_headers):
        from tests.conftest import _make_image_bytes
        content = _make_image_bytes("webp")
        resp = client.post(
            "/api/upload",
            files={"image": ("test.webp", io.BytesIO(content), "image/webp")},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["image_url"].startswith("/uploads/")
