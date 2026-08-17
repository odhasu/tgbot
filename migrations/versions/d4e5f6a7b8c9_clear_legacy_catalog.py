"""clear legacy catalog

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-17 18:15:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Orders remain intact; their nullable product_id is cleared by the FK.
    op.execute("DELETE FROM products")
    op.execute("DELETE FROM categories")


def downgrade() -> None:
    # Deleted catalog data cannot be reconstructed safely.
    pass
