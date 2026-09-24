"""add product performance indexes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6g7
Create Date: 2026-09-24
"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_products_code", "products", ["code"], unique=True)
    op.create_index("ix_products_stock_created_at", "products", ["stock", "created_at"])
    op.create_index("ix_product_categories_category_id", "product_categories", ["category_id"])
    op.create_index("ix_product_colors_color_id", "product_colors", ["color_id"])


def downgrade() -> None:
    op.drop_index("ix_product_colors_color_id", table_name="product_colors")
    op.drop_index("ix_product_categories_category_id", table_name="product_categories")
    op.drop_index("ix_products_stock_created_at", table_name="products")
    op.drop_index("ix_products_code", table_name="products")