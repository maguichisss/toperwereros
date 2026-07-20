import os
import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from fpdf import FPDF
from PIL import Image as PILImage
from app.database import get_db
from app.models import Product, User
from app.auth import require_permission

router = APIRouter()

IMG_W = 60
IMG_H = 70
CARD_W = 60
CARD_H = 85
COL_GAP = 5
ROW_GAP = 5
MARGIN = 10
HEADER_Y = 17

MONTHS_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def cover_image(path):
    dpi = 72
    target_w = int(IMG_W * dpi / 25.4)
    target_h = int(IMG_H * dpi / 25.4)
    img = PILImage.open(path)
    ratio = max(target_w / img.width, target_h / img.height)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)), PILImage.LANCZOS)
    left = (img.width - target_w) // 2
    top = (img.height - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


@router.get("/pdf")
def catalog_pdf(ids: str = "", db: Session = Depends(get_db), current_user: User = Depends(require_permission("product.view"))):
    products = db.query(Product).filter(Product.stock > 0)
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if id_list:
            products = products.filter(Product.id.in_(id_list))
    products = products.order_by(Product.name.asc()).all()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_start_str = f"{MONTHS_ES[monday.month]} {monday.day:02d}"
    week_end_str = f"{MONTHS_ES[sunday.month]} {sunday.day:02d}"
    week_num = monday.isocalendar()[1]

    for i, product in enumerate(products):
        if i % 9 == 0:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(MARGIN, 8)
            pdf.cell(90, 6, "Catalogo Toperwereros")
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(0, 6, f"Válido de {week_start_str} a {week_end_str}  |  semana {week_num}", align='R')
            pdf.set_draw_color(180, 180, 180)
            pdf.line(MARGIN, 15, 200, 15)

        col = i % 3
        row = (i % 9) // 3

        x = MARGIN + col * (CARD_W + COL_GAP)
        y = HEADER_Y + row * (CARD_H + ROW_GAP)

        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(x, y, CARD_W, CARD_H, style="DF")

        cx = x
        cy = y

        if product.image_url:
            filename = product.image_url.replace("/uploads/", "")
            path = os.path.join(os.getcwd(), "uploads", filename)
            if os.path.exists(path):
                pdf.image(cover_image(path), x=cx, y=cy, w=IMG_W, h=IMG_H)

        by = y + IMG_H + 2

        tx = x + 1.5
        tw = CARD_W - 4.5

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(tx, by)
        pdf.multi_cell(tw, 4, product.name)
        name_end = pdf.get_y()

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 115, 232)
        price_str = f"${product.price:.2f}"
        pdf.set_xy(tx, name_end)
        pdf.cell(pdf.get_string_width(price_str), 4, price_str)

        pdf.set_font("Courier", "", 8)
        pdf.set_text_color(120, 120, 120)
        code_str = product.code[:18]
        pdf.set_xy(tx + tw - pdf.get_string_width(code_str), name_end)
        pdf.cell(pdf.get_string_width(code_str), 4, code_str)

    return Response(
        content=bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=catalogo_{week_start_str.replace(' ', '')}_{week_end_str.replace(' ', '')}.pdf"},
    )
