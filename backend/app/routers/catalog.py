"""Catalog PDF generation — renders in-stock products as a printable grid."""

import io
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fpdf import FPDF
from PIL import Image as PILImage
from sqlalchemy import or_, String
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.config import safe_upload_path, escape_like
from app.models import Product, Category, Color, User
from app.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()

@dataclass(frozen=True)
class PDFConfig:
    """Layout, font, color, and content settings for the catalog PDF.

    All measurements are in millimeters.  Colors are ``(r, g, b)`` tuples.
    """

    card_w: float = 45
    card_h: float = 65
    img_w: float = 40
    img_h: float = 40
    img_inset: float = 2
    col_gap: float = 2
    row_gap: float = 2
    margin: float = 10
    header_y: float = 17
    page_h: float = 297
    bottom_margin: float = 7
    cols: int = 4
    text_gap: float = 4
    card_corner_radius: float = 2
    band_corner_radius: float = 1.0

    base_family: str = "Helvetica"
    code_family: str = "Courier"
    title_size: float = 12
    subtitle_size: float = 7
    name_size: float = 10
    name_line_height: float = 5
    code_size: float = 7
    price_size: float = 12
    placeholder_size: float = 18

    card_border: tuple[int, int, int] = (200, 200, 200)
    header_line: tuple[int, int, int] = (180, 180, 180)
    title_color: tuple[int, int, int] = (0, 0, 0)
    name_color: tuple[int, int, int] = (0, 0, 0)
    placeholder_fill: tuple[int, int, int] = (235, 235, 235)
    placeholder_text: tuple[int, int, int] = (180, 180, 180)
    code_color: tuple[int, int, int] = (120, 120, 120)
    band_fill: tuple[int, int, int] = (26, 115, 232)
    band_text: tuple[int, int, int] = (255, 255, 255)

    title: str = "Catálogo Toperwereros"
    no_category_label: str = "Sin categoría"
    filename_prefix: str = "catalogo"
    price_prefix: str = "$"
    price_decimals: int = 2
    code_max_len: int = 20
    name_clamp: float = 13.5
    band_height: float = 3.5
    jpeg_quality: int = 85

    @property
    def page_bottom(self) -> float:
        """Y position below which cards move to a new page."""
        return self.page_h - self.bottom_margin

    @property
    def grid_width(self) -> float:
        """Total width of the card grid from the left margin to its right edge."""
        return self.cols * self.card_w + (self.cols - 1) * self.col_gap


DEFAULT_PDF_CONFIG = PDFConfig()

MONTHS_ES: list[str] = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def group_and_order(
    products: list[Product], cfg: PDFConfig = DEFAULT_PDF_CONFIG
) -> list[tuple[str, list[Product]]]:
    """Group products by category and order the groups by descending count.

    Products are grouped by their first category (or the no-category label)
    and the groups are sorted from largest to smallest.  The order of products
    within each group is preserved.

    Args:
        products: Products in the desired display order.
        cfg: PDF configuration providing the no-category label.

    Returns:
        A list of ``(category_name, products)`` tuples ordered by count
        descending.
    """

    groups: dict[str, list[Product]] = {}
    for product in products:
        cat_name = product.categories[0].name if product.categories else cfg.no_category_label
        groups.setdefault(cat_name, []).append(product)
    return sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)


def cover_image(path: str, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> io.BytesIO:
    """Crop and resize an image to fill the PDF card dimensions at 72 DPI.

    The image is center-cropped to maintain aspect ratio, then saved as a
    JPEG byte buffer.

    Args:
        path: Absolute path to the source image file.
        cfg: PDF configuration for the target image size and JPEG quality.

    Returns:
        A ``BytesIO`` buffer containing the resized JPEG image data.

    Raises:
        PIL.UnidentifiedImageError: If the file is not a valid image.
        OSError: If the file cannot be opened or read.
    """

    dpi = 72
    target_w = int(cfg.img_w * dpi / 25.4)
    target_h = int(cfg.img_h * dpi / 25.4)
    img = PILImage.open(path)
    img = img.convert("RGB")
    ratio = max(target_w / img.width, target_h / img.height)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)), PILImage.LANCZOS)
    left = (img.width - target_w) // 2
    top = (img.height - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=cfg.jpeg_quality)
    buf.seek(0)
    return buf


def draw_placeholder(pdf: FPDF, x: float, y: float, initial: str, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> None:
    """Draw a gray placeholder box with the product's first letter.

    Args:
        pdf: The FPDF instance being written to.
        x: Left edge of the placeholder in mm.
        y: Top edge of the placeholder in mm.
        initial: Product name used to derive the centered letter.
        cfg: PDF configuration for the placeholder layout, fonts, and colors.
    """

    pdf.set_fill_color(*cfg.placeholder_fill)
    pdf.set_draw_color(*cfg.card_border)
    pdf.rect(x, y, cfg.img_w, cfg.img_h, style="DF", round_corners=True, corner_radius=cfg.card_corner_radius)
    if initial:
        pdf.set_font(cfg.base_family, "B", cfg.placeholder_size)
        pdf.set_text_color(*cfg.placeholder_text)
        pdf.set_xy(x, y + (cfg.img_h - cfg.placeholder_size) / 2)
        pdf.cell(cfg.img_w, cfg.placeholder_size, initial[:1].upper(), align="C")


def add_page_header(pdf: FPDF, week_start_str: str, week_end_str: str, week_num: int, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> None:
    """Add a new page with the catalog title and weekly validity header.

    Args:
        pdf: The FPDF instance being written to.
        week_start_str: Spanish month/day for the week start.
        week_end_str: Spanish month/day for the week end.
        week_num: ISO week number.
        cfg: PDF configuration for the header fonts, colors, and margins.
    """

    pdf.add_page()
    pdf.set_font(cfg.base_family, "B", cfg.title_size)
    pdf.set_text_color(*cfg.title_color)
    pdf.set_xy(cfg.margin, 8)
    pdf.cell(90, 6, cfg.title)
    pdf.set_font(cfg.base_family, "", cfg.subtitle_size)
    pdf.cell(0, 6, f"Válido de {week_start_str} a {week_end_str}  |  semana {week_num}", align='R')
    pdf.set_draw_color(*cfg.header_line)
    pdf.line(cfg.margin, 15, cfg.margin + cfg.grid_width, 15)


def draw_card(pdf: FPDF, x: float, y: float, product: Product, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> None:
    """Draw a single product card with image, name, code, and price.

    Args:
        pdf: The FPDF instance being written to.
        x: Left edge of the card in mm.
        y: Top edge of the card in mm.
        product: The product to render.
        cfg: PDF configuration for the card layout, fonts, and colors.
    """

    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*cfg.card_border)
    pdf.rect(x, y, cfg.card_w, cfg.card_h, style="DF", round_corners=True, corner_radius=cfg.card_corner_radius)

    ix = x + cfg.img_inset
    iy = y + cfg.img_inset
    image_ok = False
    if product.image_url:
        try:
            path = safe_upload_path(product.image_url)
            if path and os.path.exists(path):
                pdf.image(cover_image(path, cfg), x=ix, y=iy, w=cfg.img_w, h=cfg.img_h)
                image_ok = True
        except Exception:
            logger.warning("Omitiendo imagen inválida del producto %s (%s)", product.id, product.image_url)
    if not image_ok:
        draw_placeholder(pdf, ix, iy, product.name, cfg)

    by = y + cfg.img_h + cfg.text_gap
    tx = x + 1.5
    tw = cfg.card_w - 3

    pdf.set_font(cfg.base_family, "B", cfg.name_size)
    pdf.set_text_color(*cfg.name_color)
    pdf.set_xy(tx, by)
    pdf.multi_cell(tw, cfg.name_line_height, product.name)
    name_end = min(pdf.get_y(), y + cfg.card_h - cfg.name_clamp)

    pdf.set_font(cfg.code_family, "", cfg.code_size)
    pdf.set_text_color(*cfg.code_color)
    code_str = product.code[:cfg.code_max_len]
    pdf.set_xy(tx, name_end)
    pdf.cell(pdf.get_string_width(code_str), 3, code_str)

    band_y = y + cfg.card_h - cfg.band_height
    pdf.set_fill_color(*cfg.band_fill)
    pdf.rect(x + 1, band_y, cfg.card_w - 2, cfg.band_height, style="F", round_corners=True, corner_radius=cfg.band_corner_radius)
    pdf.set_font(cfg.base_family, "B", cfg.price_size)
    pdf.set_text_color(*cfg.band_text)
    price_str = f"{cfg.price_prefix}{product.price:.{cfg.price_decimals}f}"
    pdf.set_xy(x + 1.5, band_y + 0.3)
    pdf.cell(pdf.get_string_width(price_str), 3, price_str)


@router.get("/pdf", tags=["Catalog"], summary="Generate PDF catalog",
              description="Generate a printable PDF product catalog. 4-column card grid, 16 products per page. Only in-stock products. Optional comma-separated product IDs and free-text search filters.")
def catalog_pdf(
    ids: str = "",
    q: str = Query(None, description="Search term matched against code, name, ubicacion, price, category, and color"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.view")),
) -> Response:
    """Generate a PDF product catalog for in-stock products.

    Products are ordered by descending category product count, then name,
    and rendered in a continuous 4-column card grid (16 per page).  Each card
    contains a cropped product image, name, price, and code.  A weekly header
    with the valid date range is added to every page.

    Args:
        ids: Optional comma-separated product IDs to include.  When empty, all
            in-stock products are included.
        q: Optional search term matched against code, name, ubicacion, price,
            category, and color.
        db: Active database session.
        current_user: Authenticated user with ``product.view`` permission.

    Returns:
        A ``Response`` with ``application/pdf`` media type and a
        ``Content-Disposition`` header for download.

    Raises:
        HTTPException: 400 if ``ids`` is non-numeric; 500 if PDF generation
            fails.
    """

    products = (
        db.query(Product)
        .options(selectinload(Product.categories))
        .filter(Product.stock > 0)
    )
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(400, "El parámetro ids debe contener solo números")
        if id_list:
            products = products.filter(Product.id.in_(id_list))
    if q:
        pattern = f"%{escape_like(q)}%"
        products = products.filter(
            or_(
                Product.code.ilike(pattern, escape="\\"),
                Product.name.ilike(pattern, escape="\\"),
                Product.ubicacion.ilike(pattern, escape="\\"),
                Product.price.cast(String).ilike(pattern, escape="\\"),
                Product.categories.any(Category.name.ilike(pattern, escape="\\")),
                Product.colors.any(Color.name.ilike(pattern, escape="\\")),
            )
        )
    products = products.order_by(Product.name.asc()).all()

    try:
        cfg = DEFAULT_PDF_CONFIG
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)

        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        week_start_str = f"{MONTHS_ES[monday.month]} {monday.day:02d}"
        week_end_str = f"{MONTHS_ES[sunday.month]} {sunday.day:02d}"
        week_num = monday.isocalendar()[1]

        add_page_header(pdf, week_start_str, week_end_str, week_num, cfg)
        ordered_products = [p for _, ps in group_and_order(products, cfg) for p in ps]
        cur_y = cfg.header_y
        col = 0

        for product in ordered_products:
            if cur_y + cfg.card_h > cfg.page_bottom:
                add_page_header(pdf, week_start_str, week_end_str, week_num, cfg)
                cur_y = cfg.header_y
                col = 0
            x = cfg.margin + col * (cfg.card_w + cfg.col_gap)
            draw_card(pdf, x, cur_y, product, cfg)
            col += 1
            if col >= cfg.cols:
                col = 0
                cur_y += cfg.card_h + cfg.row_gap

        return Response(
            content=bytes(pdf.output()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={cfg.filename_prefix}_{week_start_str.replace(' ', '')}_{week_end_str.replace(' ', '')}.pdf"},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to generate catalog PDF (%d products)", len(products))
        raise HTTPException(500, "Error al generar el catálogo PDF")
