"""add category description/sort_order and settings table

Revision ID: a1c2e3f4b5d6
Revises: bd0fef4fd2db
Create Date: 2026-07-13 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2e3f4b5d6'
down_revision: Union[str, None] = 'bd0fef4fd2db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('description', sa.Text(), nullable=True))
    op.add_column(
        'categories',
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=64), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_column('categories', 'sort_order')
    op.drop_column('categories', 'description')
