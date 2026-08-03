"""Tests for catalog PDF generation and cover_image helper."""

import io
import os
import tempfile

import pytest
from PIL import Image as PILImage

from app.routers.catalog import cover_image
from app.models import Product
from decimal import Decimal


def _create_product(db, name="Widget", code="W001", price="100.00", stock=5, image_url=None):
    product = Product(name=name, code=code, price=Decimal(price), stock=stock, image_url=image_url)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


class TestCoverImage:
    def test_returns_jpeg_bytes(self, tmp_path):
        img = PILImage.new("RGB", (200, 200), color=(255, 0, 0))
        path = tmp_path / "test.jpg"
        img.save(str(path), format="JPEG")
        result = cover_image(str(path))
        assert isinstance(result, io.BytesIO)
        result.seek(0)
        header = result.read(2)
        assert header == b"\xff\xd8"

    def test_crops_and_resizes(self, tmp_path):
        img = PILImage.new("RGB", (400, 100), color=(0, 255, 0))
        path = tmp_path / "wide.jpg"
        img.save(str(path), format="JPEG")
        result = cover_image(str(path))
        result.seek(0)
        resized = PILImage.open(result)
        dpi = 72
        expected_w = int(44 * dpi / 25.4)
        expected_h = int(48 * dpi / 25.4)
        assert resized.size == (expected_w, expected_h)


class TestCatalogPDF:
    def test_pdf_success(self, client, admin_headers, db):
        _create_product(db)
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 0

    def test_pdf_with_ids_filter(self, client, admin_headers, db):
        p1 = _create_product(db, name="A", code="A01")
        p2 = _create_product(db, name="B", code="B01")
        resp = client.get(f"/api/catalog/pdf?ids={p1.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_pdf_empty_catalog(self, client, admin_headers):
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_pdf_no_auth(self, client):
        resp = client.get("/api/catalog/pdf")
        assert resp.status_code == 401

    def test_pdf_viewer_forbidden(self, client, viewer_headers):
        resp = client.get("/api/catalog/pdf", headers=viewer_headers)
        assert resp.status_code == 403

    def test_pdf_stock_zero_excluded(self, client, admin_headers, db):
        _create_product(db, name="InStock", code="IS01", stock=5)
        _create_product(db, name="OutOfStock", code="OS01", stock=0)
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200
