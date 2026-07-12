"""add product photo

Revision ID: bd0fef4fd2db
Revises: ca9edd041703
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd0fef4fd2db'
down_revision: Union[str, None] = 'ca9edd041703'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('photo_file_id', sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'photo_file_id')
