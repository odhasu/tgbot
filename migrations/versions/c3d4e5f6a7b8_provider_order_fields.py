"""add provider order fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-17 17:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "price", existing_type=sa.Numeric(12, 2), type_=sa.Numeric(14, 6), existing_nullable=False
        )
        batch_op.add_column(sa.Column("currency", sa.String(length=16), nullable=False, server_default="USD"))
        batch_op.add_column(sa.Column("provider_cost", sa.Numeric(14, 6), nullable=True))
        batch_op.add_column(sa.Column("provider_order_code", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("provider_product_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("fulfillment_status", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("bonus_quantity", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("final_quantity", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_unique_constraint("uq_orders_provider_order_code", ["provider_order_code"])

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "balance",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Numeric(14, 6),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "total_spent",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Numeric(14, 6),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "balance",
            existing_type=sa.Numeric(14, 6),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "total_spent",
            existing_type=sa.Numeric(14, 6),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_provider_order_code", type_="unique")
        batch_op.drop_column("fulfillment_status")
        batch_op.drop_column("provider_product_id")
        batch_op.drop_column("provider_order_code")
        batch_op.drop_column("final_quantity")
        batch_op.drop_column("bonus_quantity")
        batch_op.drop_column("quantity")
        batch_op.drop_column("currency")
        batch_op.drop_column("provider_cost")
        batch_op.alter_column(
            "price", existing_type=sa.Numeric(14, 6), type_=sa.Numeric(12, 2), existing_nullable=False
        )
