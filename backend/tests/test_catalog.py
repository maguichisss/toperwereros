"""Tests for catalog PDF generation and cover_image helper."""

import io
import os
import re
import tempfile
from datetime import datetime, timedelta

import pytest
from PIL import Image as PILImage
from fpdf import FPDF

from app.routers.catalog import PDFConfig, DEFAULT_PDF_CONFIG, THEMES, apply_theme, cover_image, css_color, draw_card, order_by_category_color_stock, _select_cover_products
from app.patterns import pattern_jpeg
from app.models import Product, Category, Color
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
        expected_w = int(DEFAULT_PDF_CONFIG.img_w * dpi / 25.4)
        expected_h = int(DEFAULT_PDF_CONFIG.img_h * dpi / 25.4)
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

    def test_pdf_default_format_is_pdf(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        resp = client.get("/api/catalog/pdf", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_pdf_html_format(self, client, admin_headers, db):
        _create_product(db, name="HTMLWidget", code="H001")
        resp = client.get("/api/catalog/pdf?format=html", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert b"<!DOCTYPE html>" in resp.content
        assert b"H001" in resp.content
        assert b"HTMLWidget" in resp.content

    def test_pdf_invalid_format_400(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        resp = client.get("/api/catalog/pdf?format=docx", headers=admin_headers)
        assert resp.status_code == 400

    def test_pdf_csv_format(self, client, admin_headers, db):
        _create_product(db, name="CSVWidget", code="C001", price="19.50", stock=4, image_url="x")
        prod = _create_product(db, name="Otro", code="O001", price="5.00", stock=2)
        prod.categories = [Category(name="Ropa")]
        db.commit()
        resp = client.get("/api/catalog/pdf?format=csv", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert resp.content.startswith(b"\xef\xbb\xbf")
        text = resp.content.decode("utf-8-sig")
        first = text.splitlines()[0]
        assert first == '"codigo","nombre","categorias","colores","precio","stock","ubicacion","total","fecha_creacion"'
        assert '"C001","CSVWidget","","","19.50","4","","78.00",' in text
        assert '"O001","Otro","Ropa","","5.00","2","","10.00",' in text
        assert "O001" in text

    def test_pdf_csv_escapes_field(self, client, admin_headers, db):
        _create_product(db, name='Widget "Doble", XL', code="E001", price="10.00", stock=1)
        resp = client.get("/api/catalog/pdf?format=csv", headers=admin_headers)
        assert resp.status_code == 200
        assert '"Widget ""Doble"", XL"' in resp.content.decode("utf-8-sig")

    def test_pdf_csv_stock_zero_excluded(self, client, admin_headers, db):
        _create_product(db, name="In", code="IS01", stock=5)
        _create_product(db, name="Out", code="OS01", stock=0)
        resp = client.get("/api/catalog/pdf?format=csv", headers=admin_headers)
        text = resp.content.decode("utf-8-sig")
        assert '"IS01"' in text
        assert "OS01" not in text

    def test_pdf_csv_dsl_filter(self, client, admin_headers, db):
        ropa = Category(name="Ropa")
        calzado = Category(name="Calzado")
        db.add_all([ropa, calzado])
        db.commit()
        db.refresh(ropa)
        db.refresh(calzado)
        p_ropa = _create_product(db, name="Camisa", code="RO01")
        p_ropa.categories = [ropa]
        p_cal = _create_product(db, name="Zapato", code="CA01")
        p_cal.categories = [calzado]
        db.commit()
        resp = client.get("/api/catalog/pdf?format=csv&category__eq=Ropa", headers=admin_headers)
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        assert '"RO01"' in text
        assert "CA01" not in text

    def test_pdf_csv_dsl_price_range(self, client, admin_headers, db):
        _create_product(db, name="Caro", code="P01", price="100.00", stock=1)
        _create_product(db, name="Barato", code="P02", price="20.00", stock=1)
        resp = client.get("/api/catalog/pdf?format=csv&price__gte=50", headers=admin_headers)
        text = resp.content.decode("utf-8-sig")
        assert '"P01"' in text
        assert "P02" not in text

    def test_pdf_dsl_unknown_field_400(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        resp = client.get("/api/catalog/pdf?format=csv&bogus__eq=1", headers=admin_headers)
        assert resp.status_code == 400

    def test_pdf_theme_html(self, client, admin_headers, db):
        _create_product(db, name="Widget", code="W01")
        resp = client.get("/api/catalog/pdf?format=html&theme=nocturno", headers=admin_headers)
        assert resp.status_code == 200
        assert b"#f0b429" in resp.content
        assert b'"DejaVu Sans", Helvetica' in resp.content

    def test_pdf_default_theme_is_classic(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        plain = client.get("/api/catalog/pdf?format=html", headers=admin_headers)
        explicit = client.get("/api/catalog/pdf?format=html&theme=classic", headers=admin_headers)
        assert plain.status_code == 200
        assert plain.content == explicit.content

    def test_pdf_invalid_theme_400(self, client, admin_headers, db):
        _create_product(db, name="A", code="A01")
        resp = client.get("/api/catalog/pdf?theme=unknown", headers=admin_headers)
        assert resp.status_code == 400
        assert b"The 'theme' parameter must be one of" in resp.content

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
        assert DEFAULT_PDF_CONFIG.img_h == 48
        assert DEFAULT_PDF_CONFIG.band_fill == (26, 115, 232)
        assert DEFAULT_PDF_CONFIG.title == "Catálogo Toperwereros"
        assert DEFAULT_PDF_CONFIG.band_height == 5
        assert DEFAULT_PDF_CONFIG.name_max_h == 9
        assert DEFAULT_PDF_CONFIG.price_decimals == 0
        assert DEFAULT_PDF_CONFIG.price_size == 11
        assert DEFAULT_PDF_CONFIG.code_size == 6.2

    def test_page_bottom_derived(self):
        cfg = PDFConfig(page_h=297, bottom_margin=7)
        assert cfg.page_bottom == 290

    def test_grid_width_derived(self):
        cfg = PDFConfig(cols=4, card_w=44, col_gap=4)
        assert cfg.grid_width == 188

    def test_rows_per_page_derived(self):
        assert DEFAULT_PDF_CONFIG.rows_per_page == 4


class TestRenderHTML:
    def test_css_derived_from_config(self):
        html = DEFAULT_PDF_CONFIG.render_html([], "agosto 03", "agosto 09", 32)
        assert html.startswith("<!DOCTYPE html>")
        assert "#1a73e8" in html
        assert "45mm" in html
        assert "Catálogo Toperwereros" in html

    def test_card_has_price_and_code_in_band(self):
        product = Product(name="Widget", code="W001", price=Decimal("99.00"), stock=1)
        html = DEFAULT_PDF_CONFIG.render_html([product], "a", "b", 1)
        assert "$99" in html
        assert "W001" in html
        assert "product-price" in html
        assert "product-code" in html

    def test_no_decimals(self):
        product = Product(name="Widget", code="W001", price=Decimal("1234.50"), stock=1)
        html = DEFAULT_PDF_CONFIG.render_html([product], "a", "b", 1)
        assert "$1234" in html
        assert "$1234.50" not in html


class TestOrderByCategoryColorStock:
    def test_orders_by_category_count_desc(self):
        ropa = Category(name="Ropa")
        calzado = Category(name="Calzado")
        prod = [
            Product(name=n, code=c, price=Decimal("10"), stock=1)
            for n, c in [("C1", "A01"), ("C2", "A02"), ("C3", "A03")]
        ]
        prod += [
            Product(name=n, code=c, price=Decimal("10"), stock=1)
            for n, c in [("Z1", "B01"), ("Z2", "B02")]
        ]
        for p in prod[:3]:
            p.categories = [ropa]
        for p in prod[3:]:
            p.categories = [calzado]
        ordered = order_by_category_color_stock(prod)
        assert [p.name for p in ordered] == ["C1", "C2", "C3", "Z1", "Z2"]

    def test_orders_within_category_by_color_then_stock(self):
        cat = Category(name="Ropa")
        rojo = Color(name="Rojo", hex="#ff0000")
        azul = Color(name="Azul", hex="#0000ff")
        p_red_high = Product(name="Rojo Alto", code="R1", price=Decimal("10"), stock=9)
        p_red_low = Product(name="Rojo Bajo", code="R2", price=Decimal("10"), stock=1)
        p_blue = Product(name="Azul", code="B1", price=Decimal("10"), stock=5)
        p_none = Product(name="Sin Color", code="N1", price=Decimal("10"), stock=2)
        for p in (p_red_high, p_red_low, p_blue, p_none):
            p.categories = [cat]
        p_red_high.colors = [rojo]
        p_red_low.colors = [rojo]
        p_blue.colors = [azul]
        ordered = order_by_category_color_stock([p_none, p_blue, p_red_low, p_red_high])
        assert [p.name for p in ordered] == [
            "Azul", "Rojo Bajo", "Rojo Alto", "Sin Color",
        ]

    def test_uncategorized_products_sort_last(self):
        cat = Category(name="Ropa")
        single = Product(name="Solo", code="S01", price=Decimal("10"), stock=1)
        single.categories = [cat]
        uncat = [
            Product(name=f"Suelto{i}", code=f"U{i:02d}", price=Decimal("10"), stock=1)
            for i in range(3)
        ]
        ordered = order_by_category_color_stock(uncat + [single])
        assert [p.name for p in ordered] == ["Solo", "Suelto0", "Suelto1", "Suelto2"]

    def test_uses_min_category_and_color_name(self):
        cat_z = Category(name="Zapatos")
        cat_a = Category(name="Accesorios")
        color_b = Color(name="Blanco", hex="#ffffff")
        color_a = Color(name="Azul", hex="#0000ff")
        p = Product(name="Poli", code="P01", price=Decimal("10"), stock=1)
        p.categories = [cat_z, cat_a]
        p.colors = [color_b, color_a]
        ordered = order_by_category_color_stock([p])
        assert [p.name for p in ordered] == ["Poli"]


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

    def test_band_text_baseline_inside_band(self):
        cfg = PDFConfig()
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()
        product = Product(name="Widget", code="W001", price=Decimal("99"), stock=1)
        cfg.render_card(pdf, 10, 20, product)
        content = bytes(next(iter(pdf.pages.values())).contents).decode("latin1")
        k = pdf.k
        band_top_pdf = (cfg.page_h - (20 + cfg.card_h - cfg.band_height)) * k
        band_bottom_pdf = (cfg.page_h - (20 + cfg.card_h)) * k
        for text in ("$99", "W001"):
            idx = content.find(text)
            assert idx != -1, f"text {text!r} not found in page content"
            td_pos = content.rfind("Td", 0, idx)
            segment = content[content.rfind("BT", 0, td_pos):td_pos]
            numbers = re.findall(r"\d+(?:\.\d+)?", segment)
            baseline_y = float(numbers[-1])
            assert band_bottom_pdf < baseline_y < band_top_pdf, f"{text} baseline {baseline_y} outside band"


class TestThemes:
    def test_all_override_keys_are_config_fields(self):
        from dataclasses import fields
        field_names = {f.name for f in fields(PDFConfig)}
        for theme in THEMES.values():
            assert set(theme.overrides) <= field_names, f"theme {theme.name} has unknown overrides"

    def test_classic_has_no_overrides(self):
        assert THEMES["classic"].overrides == {}
        assert apply_theme(DEFAULT_PDF_CONFIG, "classic") == DEFAULT_PDF_CONFIG

    def test_every_theme_renders_pdf_and_html(self):
        product = Product(name="Producto de Prueba", code="ABC123", price=Decimal("99"), stock=1)
        for name in THEMES:
            cfg = apply_theme(DEFAULT_PDF_CONFIG, name)
            pdf_bytes = cfg.render_pdf([product], "agosto 03", "agosto 09", 32)
            assert pdf_bytes.startswith(b"%PDF")
            assert len(pdf_bytes) > 0
            html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
            assert css_color(cfg.band_fill) in html
            assert cfg.font_family_css in html

    def test_page_fill_differs_per_theme(self):
        palettes = {name: apply_theme(DEFAULT_PDF_CONFIG, name) for name in THEMES}
        assert len({cfg.page_fill for cfg in palettes.values()}) > 1
        assert len({cfg.band_fill for cfg in palettes.values()}) > 1

    def test_expected_theme_set(self):
        assert set(THEMES) == {
            "classic", "nocturno", "kraft", "elegante",
            "marino", "sol", "cyber", "vino", "rosa",
            "arcoiris", "nebulosa", "triangulos", "olas", "mandala",
            "aurora", "confeti", "galaxia", "marco", "flores",
        }

    def test_widened_margin_themes_keep_four_rows(self):
        widened = ["nebulosa", "aurora", "confeti", "galaxia", "marco", "flores"]
        assert set(widened) <= set(THEMES)
        for name in widened:
            cfg = apply_theme(DEFAULT_PDF_CONFIG, name)
            assert (cfg.margin, cfg.header_y, cfg.bottom_margin) == (13, 20, 11), name
            assert cfg.rows_per_page == 4, name

    def test_pattern_themes_embed_background(self):
        product = Product(name="P", code="C1", price=Decimal("10"), stock=1)
        pattern_themes = [t for t in THEMES.values() if t.overrides.get("page_pattern")]
        assert len(pattern_themes) == 10
        for theme in pattern_themes:
            cfg = apply_theme(DEFAULT_PDF_CONFIG, theme.name)
            html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
            assert "data:image/jpeg;base64," in html
            assert cfg.render_pdf([product], "agosto 03", "agosto 09", 32).startswith(b"%PDF")

    def test_pattern_images_are_valid_jpeg(self):
        pids = ("rainbow", "nebula", "triangles", "waves", "mandala",
                "aurora", "confeti", "galaxia", "marco", "flores")
        jpegs = {pid: pattern_jpeg(pid) for pid in pids}
        for pid, data in jpegs.items():
            assert data[:2] == b"\xff\xd8", f"pattern {pid} is not a JPEG"
            assert len(data) > 1000
        assert len({data for data in jpegs.values()}) == 10


class TestCatalogCover:
    def test_html_has_cover_with_brand_and_validity(self):
        product = Product(name="Widget", code="W001", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
        assert 'class="page page-cover"' in html
        assert 'class="page-index"' not in html
        assert "Índice" not in html
        assert "Toperwereros" in html
        assert "Válido de agosto 03 a agosto 09" in html
        assert "semana 32" in html
        assert "527207965588" in html

    def test_cover_whatsapp_link_uses_cover_message(self):
        product = Product(name="Widget", code="W001", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
        assert "cover-contact__wa" in html
        assert "https://wa.me/527207965588?text=" in html
        assert "quisiera%20preguntar" in html
        assert "cover-contact__wa-icon" in html
        assert "M17.472 14.382" in html
        assert "viewBox" in html
        assert "+527207965588" not in html
        assert "cover-contact__num" not in html
        assert "720 796 5588" in html
        assert "cover-contact__wa-num" in html

    def test_cover_label_and_phone_display(self):
        product = Product(name="Widget", code="W001", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
        assert "Pregunta por nuestro catálogo completo" in html
        from app.routers.catalog import _cover_phone_display
        assert _cover_phone_display("527207965588") == "720 796 5588"
        assert _cover_phone_display("9995299") == "999 5299"
        assert _cover_phone_display("5599") == "5599"
        assert _cover_phone_display("55512345551234") == "234 555 1234"

    def test_cover_gallery_renders_up_to_six_products(self):
        from app.config import UPLOAD_DIR
        products = []
        for i in range(8):
            filename = f"cover_test_{os.getpid()}_{i}.jpg"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(pattern_jpeg("rainbow"))
            products.append(
                Product(name=f"P{i}", code=f"C{i:02d}", price=Decimal("10"), stock=2, image_url=f"/uploads/{filename}")
            )
        try:
            cfg = PDFConfig()
            html = cfg.render_cover_html(products, "agosto 03", "agosto 09", 32)
            assert html.count("cover-gallery-cell") == 6
            assert "cover-logo" not in html or "data:image/png" in html
            selected = _select_cover_products(products, 32, cfg.cover_sample_count, cfg)
            assert len(selected) == 6
        finally:
            for i in range(8):
                filepath = os.path.join(UPLOAD_DIR, f"cover_test_{os.getpid()}_{i}.jpg")
                if os.path.exists(filepath):
                    os.remove(filepath)

    def test_cover_gallery_safe_without_images(self):
        products = [Product(name="P1", code="C01", price=Decimal("10"), stock=2)]
        cfg = PDFConfig()
        assert _select_cover_products(products, 32, cfg.cover_sample_count, cfg) == []
        html = cfg.render_cover_html(products, "agosto 03", "agosto 09", 32)
        assert html.count("cover-gallery-cell") == 6

    def test_cover_selection_is_deterministic_by_week(self):
        from app.config import UPLOAD_DIR
        products = []
        for i in range(10):
            filename = f"cover_det_{os.getpid()}_{i}.jpg"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(pattern_jpeg("rainbow"))
            products.append(
                Product(name=f"P{i}", code=f"C{i:02d}", price=Decimal("10"), stock=2, image_url=f"/uploads/{filename}")
            )
        try:
            cfg = PDFConfig()
            a = _select_cover_products(products, 32, 6, cfg)
            b = _select_cover_products(products, 32, 6, cfg)
            c = _select_cover_products(products, 33, 6, cfg)
            assert [p.code for p in a] == [p.code for p in b]
            assert len({p.code for p in a}) == 6
            assert [p.code for p in a] != [p.code for p in c]
        finally:
            for i in range(10):
                filepath = os.path.join(UPLOAD_DIR, f"cover_det_{os.getpid()}_{i}.jpg")
                if os.path.exists(filepath):
                    os.remove(filepath)

    def test_pdf_renders_with_contact(self):
        product = Product(name="Widget", code="W001", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        pdf = cfg.render_pdf([product], "agosto 03", "agosto 09", 32)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 0
        assert b"wa.me/527207965588" in pdf

    def test_empty_catalog_pdf(self):
        cfg = PDFConfig()
        pdf = cfg.render_pdf([], "agosto 03", "agosto 09", 32)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 0


class TestCardWhatsApp:
    def test_card_html_uses_wa_link_when_contact_set(self):
        product = Product(name="Cafetera Italiana", code="CF-01", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        html = cfg._card_html(product)
        assert 'class="card-wa"' in html
        assert "https://wa.me/527207965588" in html
        assert "Cafetera%20Italiana" in html
        assert "CF-01" in html
        assert "Escríbenos a" in html
        assert 'class="product-code"' not in html

    def test_card_html_keeps_code_without_contact(self):
        product = Product(name="Cafetera", code="CF-01", price=Decimal("99"), stock=1)
        html = PDFConfig()._card_html(product)
        assert 'class="product-code"' in html
        assert "CF-01" in html
        assert "card-wa" not in html

    def test_render_html_embeds_wa_link(self):
        product = Product(name="Cafetera Italiana", code="CF-01", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        html = cfg.render_html([product], "agosto 03", "agosto 09", 32)
        assert 'class="card-wa" href="https://wa.me/527207965588?text=Hola%2C%20sigue%20disponible' in html

    def test_pdf_embeds_clickable_wa_link(self):
        product = Product(name="Cafetera", code="CF-01", price=Decimal("99"), stock=1)
        cfg = PDFConfig(contact_whatsapp="527207965588")
        pdf = cfg.render_pdf([product], "agosto 03", "agosto 09", 32)
        assert b"/Annots" in pdf
        assert b"wa.me/527207965588" in pdf
        assert b"/XObject" in pdf
        assert b"/SMask" in pdf

    def test_whatsapp_icon_png_is_small_green_silhouette(self):
        from app.routers.catalog import _whatsapp_icon_png, _WHATSAPP_ICON_PATH
        from PIL import Image
        import io
        png = _whatsapp_icon_png()
        img = Image.open(io.BytesIO(png))
        assert img.size == (256, 256)
        assert img.mode == "RGBA"
        assert len(png) < 10000
        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        assert bbox is not None and bbox[0] >= 0
        assert alpha.point(lambda a: 255 if a > 127 else 0).getextrema() == (0, 255)
        assert _WHATSAPP_ICON_PATH.startswith("M17.472 14.382")

    def test_whatsapp_icon_png_supports_custom_color(self):
        from app.routers.catalog import _whatsapp_icon_png
        from PIL import Image
        import io
        white_png = _whatsapp_icon_png((255, 255, 255))
        img = Image.open(io.BytesIO(white_png))
        assert img.size == (256, 256)
        assert img.mode == "RGBA"
        colors = img.getcolors(maxcolors=1 << 24)
        assert colors is not None
        colored = {(r, g, b) for _, (r, g, b, a) in colors if a > 60}
        assert colored and colored == {(255, 255, 255)}
