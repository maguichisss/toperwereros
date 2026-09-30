"""add dashboard performance indexes

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-29
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_sales_created_at", "sales", ["created_at"])
    op.create_index("ix_layaways_status", "layaways", ["status"])
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_sale_items_product_id", table_name="sale_items")
    op.drop_index("ix_layaways_status", table_name="layaways")
    op.drop_index("ix_sales_created_at", table_name="sales")
