"""add login lockout

Revision ID: a1b2c3d4e5f6
Revises: 9f1f74f4c202
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9f1f74f4c202'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add failed_login_attempts and locked_until columns to users table."""
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove lockout columns from users table."""
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
