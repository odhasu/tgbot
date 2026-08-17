"""Order ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(default="", nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    provider_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(16), default="USD", nullable=False)
    provider_order_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    provider_product_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fulfillment_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    bonus_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    final_quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    has_warranty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.COMPLETED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    product: Mapped["Product | None"] = relationship(back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order id={self.id} user_id={self.user_id} status={self.status}>"
