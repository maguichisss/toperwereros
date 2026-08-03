"""Catalog output generation — renders in-stock products as PDF or HTML."""

import io
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape

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


def css_color(color: tuple[int, int, int]) -> str:
    """Convert an ``(r, g, b)`` tuple to a CSS ``#rrggbb`` string."""
    return "#{:02x}{:02x}{:02x}".format(*color)


@dataclass(frozen=True)
class PDFConfig:
    """Layout, font, color, and content settings for the catalog output.

    All measurements are in millimeters, font sizes in points, and colors as
    ``(r, g, b)`` tuples.  Values mirror the CSS variables in
    ``docs/card-mockup.html`` so the HTML and PDF renderings stay identical.
    """

    # --- geometry (mm) ---
    page_w: float = 210
    page_h: float = 297
    margin: float = 10
    cols: int = 4
    card_w: float = 45
    card_h: float = 65
    col_gap: float = 2
    row_gap: float = 2
    card_corner_radius: float = 2
    header_y: float = 17
    bottom_margin: float = 7

    # --- image / placeholder ---
    img_w: float = 40
    img_h: float = 48
    img_inset: float = 2
    img_margin_right: float = 3
    placeholder_size: float = 18

    # --- name ---
    name_size: float = 10
    name_line_height: float = 4.5
    name_max_h: float = 9
    name_margin_x: float = 1.5

    # --- price band ---
    band_height: float = 5
    band_corner_radius: float = 1.0
    band_margin_x: float = 1
    price_size: float = 11
    price_padding_x: float = 1.5

    # --- page header ---
    title_size: float = 12
    subtitle_size: float = 7
    title_x: float = 10
    title_y: float = 8
    subtitle_right: float = 10
    rule_y: float = 15

    # --- fonts ---
    base_family: str = "Helvetica"
    code_family: str = "Courier"
    code_size: float = 6.2

    # --- colors ---
    card_fill: tuple[int, int, int] = (255, 255, 255)
    card_border: tuple[int, int, int] = (200, 200, 200)
    header_line: tuple[int, int, int] = (180, 180, 180)
    title_color: tuple[int, int, int] = (0, 0, 0)
    name_color: tuple[int, int, int] = (0, 0, 0)
    placeholder_fill: tuple[int, int, int] = (235, 235, 235)
    placeholder_text: tuple[int, int, int] = (180, 180, 180)
    band_fill: tuple[int, int, int] = (26, 115, 232)
    band_text: tuple[int, int, int] = (255, 255, 255)

    # --- content ---
    title: str = "Catálogo Toperwereros"
    no_category_label: str = "Sin categoría"
    filename_prefix: str = "catalogo"
    price_prefix: str = "$"
    price_decimals: int = 0
    code_max_len: int = 20
    jpeg_quality: int = 85

    @property
    def page_bottom(self) -> float:
        """Y position below which cards move to a new page."""
        return self.page_h - self.bottom_margin

    @property
    def grid_width(self) -> float:
        """Total width of the card grid from the left margin to its right edge."""
        return self.cols * self.card_w + (self.cols - 1) * self.col_gap

    @property
    def rows_per_page(self) -> int:
        """Maximum number of card rows that fit on a page."""
        return max(1, int((self.page_bottom - self.header_y + self.row_gap) // (self.card_h + self.row_gap)))

    def _image_exists(self, url: str) -> bool:
        try:
            path = safe_upload_path(url)
            return bool(path and os.path.exists(path))
        except Exception:
            return False

    def render_page_header(self, pdf: FPDF, week_start_str: str, week_end_str: str, week_num: int) -> None:
        """Add a new page with the catalog title and weekly validity header."""
        pdf.add_page()
        pdf.set_font(self.base_family, "B", self.title_size)
        pdf.set_text_color(*self.title_color)
        pdf.set_xy(self.margin, self.title_y)
        pdf.cell(90, 6, self.title)
        pdf.set_font(self.base_family, "", self.subtitle_size)
        pdf.cell(0, 6, f"Válido de {week_start_str} a {week_end_str}  |  semana {week_num}", align="R")
        pdf.set_draw_color(*self.header_line)
        pdf.line(self.margin, self.rule_y, self.margin + self.grid_width, self.rule_y)

    def render_card(self, pdf: FPDF, x: float, y: float, product: Product) -> None:
        """Draw one product card: image, name, and price band with code."""
        pdf.set_fill_color(*self.card_fill)
        pdf.set_draw_color(*self.card_border)
        pdf.rect(x, y, self.card_w, self.card_h, style="DF", round_corners=True, corner_radius=self.card_corner_radius)

        ix = x + self.img_inset
        iy = y + self.img_inset
        image_ok = False
        if product.image_url:
            try:
                path = safe_upload_path(product.image_url)
                if path and os.path.exists(path):
                    pdf.image(cover_image(path, self), x=ix, y=iy, w=self.img_w, h=self.img_h)
                    image_ok = True
            except Exception:
                logger.warning("Omitiendo imagen inválida del producto %s (%s)", product.id, product.image_url)
        if not image_ok:
            draw_placeholder(pdf, ix, iy, product.name, self)

        tx = x + self.name_margin_x
        tw = self.card_w - 2 * self.name_margin_x
        name_top = iy + self.img_h
        pdf.set_font(self.base_family, "B", self.name_size)
        pdf.set_text_color(*self.name_color)
        name = product.name
        max_two_lines = 2 * tw
        if pdf.get_string_width(name) > max_two_lines:
            lo, hi = 0, len(name)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if pdf.get_string_width(name[:mid]) <= max_two_lines:
                    lo = mid
                else:
                    hi = mid - 1
            name = name[:lo]
        pdf.set_xy(tx, name_top)
        pdf.multi_cell(tw, self.name_line_height, name)

        band_y = y + self.card_h - self.band_height
        band_x = x + self.band_margin_x
        band_w = self.card_w - 2 * self.band_margin_x
        pdf.set_fill_color(*self.band_fill)
        pdf.rect(band_x, band_y, band_w, self.band_height, style="F", round_corners=True, corner_radius=self.band_corner_radius)

        pdf.set_font(self.base_family, "B", self.price_size)
        pdf.set_text_color(*self.band_text)
        price_str = f"{self.price_prefix}{product.price:.{self.price_decimals}f}"
        pdf.set_xy(band_x + self.price_padding_x, band_y)
        pdf.cell(pdf.get_string_width(price_str), self.band_height, price_str)

        code_str = product.code[:self.code_max_len]
        pdf.set_font(self.code_family, "", self.code_size)
        code_w = pdf.get_string_width(code_str)
        code_x = band_x + band_w - self.price_padding_x - code_w
        pdf.set_xy(code_x, band_y)
        pdf.cell(code_w, self.band_height, code_str)

    def render_pdf(self, products: list[Product], week_start_str: str, week_end_str: str, week_num: int) -> bytes:
        """Render the ordered products to a multi-page PDF byte string."""
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)
        self.render_page_header(pdf, week_start_str, week_end_str, week_num)
        for idx, page_products in enumerate(paginate(products, self)):
            if idx > 0:
                self.render_page_header(pdf, week_start_str, week_end_str, week_num)
            for i, product in enumerate(page_products):
                col = i % self.cols
                row = i // self.cols
                x = self.margin + col * (self.card_w + self.col_gap)
                y = self.header_y + row * (self.card_h + self.row_gap)
                self.render_card(pdf, x, y, product)
        return bytes(pdf.output())

    def _card_html(self, product: Product) -> str:
        name = escape(product.name)
        code = escape(product.code[:self.code_max_len])
        price = escape(f"{self.price_prefix}{product.price:.{self.price_decimals}f}")
        if product.image_url and self._image_exists(product.image_url):
            image = f'<img src="{escape(product.image_url)}" alt="">'
        else:
            image = f'<span class="initial">{escape(product.name[:1].upper())}</span>'
        return (
            f'<div class="card"><div class="product-image">{image}</div>'
            f'<div class="product-name">{name}</div>'
            f'<div class="product-price"><span>{price}</span>'
            f'<span class="product-code">{code}</span></div></div>'
        )

    def render_html(self, products: list[Product], week_start_str: str, week_end_str: str, week_num: int) -> str:
        """Render the ordered products to a printable HTML document."""
        parts = [
            "<!DOCTYPE html>",
            '<html lang="es"><head><meta charset="utf-8">',
            f"<title>{escape(self.title)}</title>",
            f"<style>{self._css()}</style>",
            "</head><body>",
        ]
        for page_products in paginate(products, self):
            parts.append('<div class="page">')
            parts.append('<header class="page-header">')
            parts.append(f'<div class="page-title">{escape(self.title)}</div>')
            parts.append(
                f'<div class="page-subtitle">Válido de {escape(week_start_str)} a {escape(week_end_str)}'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;semana {week_num}</div>'
            )
            parts.append('<div class="page-rule"></div></header>')
            parts.append('<main class="page-body">')
            for i in range(0, len(page_products), self.cols):
                parts.append('<div class="row">')
                parts.extend(self._card_html(p) for p in page_products[i:i + self.cols])
                parts.append("</div>")
            parts.append("</main></div>")
        parts.append("</body></html>")
        return "\n".join(parts)

    def _css(self) -> str:
        mm = lambda v: f"{v:g}mm"
        pt = lambda v: f"{v:g}pt"
        c = css_color
        return f"""
:root {{
  --page-w: {mm(self.page_w)};
  --page-h: {mm(self.page_h)};
  --page-radius: 4px;

  --header-h: {mm(self.header_y)};
  --title-x: {mm(self.title_x)};
  --title-y: {mm(self.title_y)};
  --title-font: {pt(self.title_size)};
  --subtitle-right: {mm(self.subtitle_right)};
  --subtitle-y: {mm(self.title_y)};
  --subtitle-font: {pt(self.subtitle_size)};
  --rule-y: {mm(self.rule_y)};
  --rule-h: 0.6px;

  --body-margin-left: {mm(self.margin)};
  --body-w: calc(var(--cols) * var(--card-w) + (var(--cols) - 1) * var(--col-gap));
  --row-gap: {mm(self.row_gap)};
  --col-gap: {mm(self.col_gap)};
  --cols: {self.cols};

  --card-w: {mm(self.card_w)};
  --card-h: {mm(self.card_h)};
  --card-radius: {mm(self.card_corner_radius)};

  --img-margin: {mm(self.img_inset)} {mm(self.img_margin_right)} 0 {mm(self.img_inset)};
  --img-w: {mm(self.img_w)};
  --img-h: {mm(self.img_h)};
  --img-radius: {mm(self.card_corner_radius)};
  --initial-font: {pt(self.placeholder_size)};

  --name-margin: 0 {mm(self.name_margin_x)};
  --name-font: {pt(self.name_size)};
  --name-line-height: {mm(self.name_line_height)};
  --name-max-h: {mm(self.name_max_h)};

  --code-font: {pt(self.code_size)};

  --price-margin: auto {mm(self.band_margin_x)} 0;
  --price-h: {mm(self.band_height)};
  --price-radius: {mm(self.band_corner_radius)};
  --price-padding-x: {mm(self.price_padding_x)};
  --price-font: {pt(self.price_size)};

  --color-surface: {c(self.card_fill)};
  --color-text: {c(self.name_color)};
  --color-card-border: {c(self.card_border)};
  --color-header-rule: {c(self.header_line)};
  --color-image-bg: {c(self.placeholder_fill)};
  --color-image-initial: {c(self.placeholder_text)};
  --color-band: {c(self.band_fill)};
  --color-band-text: {c(self.band_text)};
}}

* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #fff; font-family: Helvetica, Arial, sans-serif; }}

@page {{ size: {mm(self.page_w)} {mm(self.page_h)}; margin: 0; }}

.page {{ position: relative; width: var(--page-w); height: var(--page-h); background: var(--color-surface); page-break-after: always; }}
.page:last-child {{ page-break-after: auto; }}

.page-header {{ position: relative; height: var(--header-h); }}
.page-title {{ position: absolute; left: var(--title-x); top: var(--title-y); font-size: var(--title-font); font-weight: bold; color: var(--color-text); white-space: nowrap; }}
.page-subtitle {{ position: absolute; right: var(--subtitle-right); top: var(--subtitle-y); font-size: var(--subtitle-font); color: var(--color-text); white-space: nowrap; }}
.page-rule {{ position: absolute; left: var(--body-margin-left); top: var(--rule-y); width: var(--body-w); height: var(--rule-h); background: var(--color-header-rule); }}

.page-body {{ display: flex; flex-direction: column; gap: var(--row-gap); margin-left: var(--body-margin-left); width: var(--body-w); }}
.row {{ display: grid; grid-template-columns: repeat(var(--cols), var(--card-w)); gap: var(--col-gap); }}

.card {{ display: flex; flex-direction: column; width: var(--card-w); height: var(--card-h); background: var(--color-surface); border: 1px solid var(--color-card-border); border-radius: var(--card-radius); break-inside: avoid; }}

.product-image {{ margin: var(--img-margin); width: var(--img-w); height: var(--img-h); background: var(--color-image-bg); border: 1px solid var(--color-card-border); border-radius: var(--img-radius); display: flex; align-items: center; justify-content: center; overflow: hidden; }}
.product-image img {{ width: 100%; height: 100%; object-fit: cover; }}
.product-image .initial {{ font-size: var(--initial-font); font-weight: bold; color: var(--color-image-initial); }}

.product-name {{ margin: var(--name-margin); font-size: var(--name-font); font-weight: bold; line-height: var(--name-line-height); color: var(--color-text); max-height: var(--name-max-h); overflow: hidden; }}

.product-code {{ font-family: "Courier New", monospace; font-size: var(--code-font); font-weight: normal; color: var(--color-band-text); white-space: nowrap; }}

.product-price {{ margin: var(--price-margin); height: var(--price-h); background: var(--color-band); border-radius: var(--price-radius); display: flex; justify-content: space-between; align-items: center; padding: 0 var(--price-padding-x); font-size: var(--price-font); font-weight: bold; color: var(--color-band-text); white-space: nowrap; }}
"""


DEFAULT_PDF_CONFIG = PDFConfig()


def paginate(products: list[Product], cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> list[list[Product]]:
    """Split a product list into pages of ``cols * rows_per_page`` cards."""
    per_page = cfg.cols * cfg.rows_per_page
    return [products[i:i + per_page] for i in range(0, len(products), per_page)]

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
        pdf.set_xy(x, y)
        pdf.cell(cfg.img_w, cfg.img_h, initial[:1].upper(), align="C")


def add_page_header(pdf: FPDF, week_start_str: str, week_end_str: str, week_num: int, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> None:
    """Add a new page with the catalog title and weekly validity header.

    Args:
        pdf: The FPDF instance being written to.
        week_start_str: Spanish month/day for the week start.
        week_end_str: Spanish month/day for the week end.
        week_num: ISO week number.
        cfg: PDF configuration for the header fonts, colors, and margins.
    """

    cfg.render_page_header(pdf, week_start_str, week_end_str, week_num)


def draw_card(pdf: FPDF, x: float, y: float, product: Product, cfg: PDFConfig = DEFAULT_PDF_CONFIG) -> None:
    """Draw a single product card with image, name, and price band.

    Args:
        pdf: The FPDF instance being written to.
        x: Left edge of the card in mm.
        y: Top edge of the card in mm.
        product: The product to render.
        cfg: PDF configuration for the card layout, fonts, and colors.
    """

    cfg.render_card(pdf, x, y, product)


@router.get("/pdf", tags=["Catalog"], summary="Generate PDF catalog",
              description="Generate a printable product catalog as PDF (default) or HTML. 4-column card grid, 16 products per page. Only in-stock products. Optional comma-separated product IDs and free-text search filters.")
def catalog_pdf(
    ids: str = "",
    q: str = Query(None, description="Search term matched against code, name, ubicacion, price, category, and color"),
    format: str = Query("pdf", description="Output format: 'pdf' (default) or 'html'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product.view")),
) -> Response:
    """Generate a product catalog for in-stock products as PDF or HTML.

    Products are ordered by descending category product count, then name,
    and rendered in a continuous 4-column card grid (16 per page).  Each card
    contains a cropped product image, name, and a price band with the code.
    A weekly header with the valid date range is added to every page.

    Args:
        ids: Optional comma-separated product IDs to include.  When empty, all
            in-stock products are included.
        q: Optional search term matched against code, name, ubicacion, price,
            category, and color.
        format: Output format, ``"pdf"`` (default) or ``"html"``.
        db: Active database session.
        current_user: Authenticated user with ``product.view`` permission.

    Returns:
        A ``Response`` with the catalog as a downloadable PDF or viewable HTML.

    Raises:
        HTTPException: 400 if ``ids`` is non-numeric or ``format`` is invalid;
            500 if generation fails.
    """

    if format not in ("pdf", "html"):
        raise HTTPException(400, "El parámetro format debe ser 'pdf' o 'html'")

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

        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        week_start_str = f"{MONTHS_ES[monday.month]} {monday.day:02d}"
        week_end_str = f"{MONTHS_ES[sunday.month]} {sunday.day:02d}"
        week_num = monday.isocalendar()[1]

        ordered_products = [p for _, ps in group_and_order(products, cfg) for p in ps]

        if format == "html":
            html = cfg.render_html(ordered_products, week_start_str, week_end_str, week_num)
            return Response(
                content=html,
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f"inline; filename={cfg.filename_prefix}.html"},
            )

        content = cfg.render_pdf(ordered_products, week_start_str, week_end_str, week_num)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={cfg.filename_prefix}_{week_start_str.replace(' ', '')}_{week_end_str.replace(' ', '')}.pdf"},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to generate catalog (%d products)", len(products))
        raise HTTPException(500, "Error al generar el catálogo PDF")
