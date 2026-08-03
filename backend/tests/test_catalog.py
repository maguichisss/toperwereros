"""Tests for catalog PDF generation and cover_image helper."""

import io
import os
import tempfile

import pytest
from PIL import Image as PILImage
from fpdf import FPDF

from app.routers.catalog import PDFConfig, DEFAULT_PDF_CONFIG, cover_image, draw_card, group_and_order
from app.models import Product, Category
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
        expected_w = int(40 * dpi / 25.4)
        expected_h = int(40 * dpi / 25.4)
        assert resized.size == (expected_w, expected_h)

    def test_converts_rgba_png_to_jpeg(self, tmp_path):
        img = PILImage.new("RGBA", (200, 200), color=(255, 0, 0, 128))
        path = tmp_path / "alpha.png"
        img.save(str(path), format="PNG")
        result = cover_image(str(path))
        result.seek(0)
        assert result.read(2) == b"\xff\xd8"


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

    def test_pdf_viewer_allowed(self, client, viewer_headers):
        resp = client.get("/api/catalog/pdf", headers=viewer_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_pdf_stock_zero_excluded(self, client, admin_headers, db):
        _create_product(db, name="InStock", code="IS01", stock=5)
        _create_product(db, name="OutOfStock", code="OS01", stock=0)
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200

    def test_pdf_invalid_ids_400(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        resp = client.get("/api/catalog/pdf?ids=abc", headers=admin_headers)
        assert resp.status_code == 400

    def test_pdf_q_filter(self, client, admin_headers, db):
        _create_product(db, name="AlphaWidget", code="AW01")
        _create_product(db, name="BetaGadget", code="BG01")
        resp = client.get("/api/catalog/pdf?q=widget", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_pdf_q_no_match(self, client, admin_headers, db):
        _create_product(db, name="AlphaWidget", code="AW01")
        resp = client.get("/api/catalog/pdf?q=noexiste", headers=admin_headers)
        assert resp.status_code == 200

    def test_pdf_skips_corrupt_image(self, client, admin_headers, db):
        from app.config import UPLOAD_DIR
        filename = "corrupt_test_%s.jpg" % os.getpid()
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(b"not a real image")
        try:
            _create_product(db, name="Corrupt", code="CR01", image_url=f"/uploads/{filename}")
            resp = client.get("/api/catalog/pdf", headers=admin_headers)
            assert resp.status_code == 200
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_pdf_groups_by_category(self, client, admin_headers, db):
        cat_a = Category(name="Ropa")
        cat_b = Category(name="Calzado")
        db.add_all([cat_a, cat_b])
        db.commit()
        db.refresh(cat_a)
        db.refresh(cat_b)
        for name, code, cat in [
            ("Camisa", "RO01", cat_a),
            ("Pantalón", "RO02", cat_a),
            ("Zapato", "CA01", cat_b),
        ]:
            product = _create_product(db, name=name, code=code)
            product.categories = [cat]
            db.commit()
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.content) > 0


class TestPDFConfig:
    def test_defaults(self):
        assert DEFAULT_PDF_CONFIG.card_w == 45
        assert DEFAULT_PDF_CONFIG.card_h == 65
        assert DEFAULT_PDF_CONFIG.img_w == 40
        assert DEFAULT_PDF_CONFIG.img_h == 40
        assert DEFAULT_PDF_CONFIG.band_fill == (26, 115, 232)
        assert DEFAULT_PDF_CONFIG.title == "Catálogo Toperwereros"

    def test_page_bottom_derived(self):
        cfg = PDFConfig(page_h=297, bottom_margin=7)
        assert cfg.page_bottom == 290

    def test_grid_width_derived(self):
        cfg = PDFConfig(cols=4, card_w=44, col_gap=4)
        assert cfg.grid_width == 188


class TestGroupAndOrder:
    def test_orders_groups_by_count_desc(self):
        ropa = Category(name="Ropa")
        calzado = Category(name="Calzado")
        sin = Category(name="Sin categoría")
        cat_a = [Product(name=n, code=c, price=Decimal("10"), stock=1) for n, c in
                 [("C1", "A01"), ("C2", "A02"), ("C3", "A03")]]
        cat_b = [Product(name=n, code=c, price=Decimal("10"), stock=1) for n, c in
                 [("Z1", "B01"), ("Z2", "B02")]]
        cat_c = [Product(name=n, code=c, price=Decimal("10"), stock=1) for n, c in
                 [("S1", "C01")]]
        for p in cat_a:
            p.categories = [ropa]
        for p in cat_b:
            p.categories = [calzado]
        for p in cat_c:
            p.categories = [sin]
        groups = group_and_order(cat_a + cat_b + cat_c)
        assert [name for name, _ in groups] == ["Ropa", "Calzado", "Sin categoría"]

    def test_preserves_within_group_order(self):
        cat = Category(name="Ropa")
        products = []
        for name, code in [("Zeta", "Z01"), ("Alpha", "A01"), ("Beta", "B01")]:
            p = Product(name=name, code=code, price=Decimal("10"), stock=1)
            p.categories = [cat]
            products.append(p)
        groups = group_and_order(products)
        assert [p.name for p in groups[0][1]] == ["Zeta", "Alpha", "Beta"]

    def test_no_category_label_used(self):
        p = Product(name="Suelto", code="S01", price=Decimal("10"), stock=1)
        groups = group_and_order([p], PDFConfig(no_category_label="Varios"))
        assert groups[0][0] == "Varios"


class TestCustomPDFConfig:
    def test_custom_config_renders(self):
        cfg = PDFConfig(card_w=50, card_h=70, name_size=10, band_fill=(0, 0, 0))
        product = Product(name="Producto de prueba", code="ABC123", price=Decimal("99.99"), stock=1)
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()
        draw_card(pdf, 10, 20, product, cfg)
        output = bytes(pdf.output())
        assert len(output) > 0
        assert output.startswith(b"%PDF")
