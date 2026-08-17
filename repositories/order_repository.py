"""Data access for Order records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from models.enums import OrderStatus
from models.order import Order
from models.user import User
from repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class VouchEntry:
    buyer_name: str
    product_name: str
    price: Decimal
    created_at: datetime


class OrderRepository(BaseRepository):
    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_by_provider_order_code(self, order_code: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.provider_order_code == order_code)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        product_id: int | None,
        product_name: str,
        price: Decimal,
        has_warranty: bool = False,
        status: OrderStatus = OrderStatus.COMPLETED,
        currency: str = "USD",
        provider_order_code: str | None = None,
        provider_product_id: str | None = None,
        fulfillment_status: str | None = None,
        provider_cost: Decimal | None = None,
        quantity: int = 1,
        bonus_quantity: int = 0,
        final_quantity: int = 1,
    ) -> Order:
        order = Order(
            user_id=user_id,
            product_id=product_id,
            product_name=product_name,
            price=price,
            provider_cost=provider_cost,
            currency=currency,
            provider_order_code=provider_order_code,
            provider_product_id=provider_product_id,
            fulfillment_status=fulfillment_status,
            quantity=quantity,
            bonus_quantity=bonus_quantity,
            final_quantity=final_quantity,
            has_warranty=has_warranty,
            status=status,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def list_by_user(self, user_id: int, limit: int = 20) -> list[Order]:
        result = await self.session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Order]:
        result = await self.session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        await self.session.flush()
        return order

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(Order.id)))
        return result.scalar_one()

    async def total_revenue(self) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Order.price), 0)).where(
                Order.status == OrderStatus.COMPLETED
            )
        )
        return Decimal(result.scalar_one())

    async def total_provider_cost(self) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Order.provider_cost), 0)).where(
                Order.status == OrderStatus.COMPLETED
            )
        )
        return Decimal(result.scalar_one())

    async def total_products_delivered(self) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Order.final_quantity), 0)).where(
                Order.status == OrderStatus.COMPLETED
            )
        )
        return int(result.scalar_one())

    async def list_recent_vouches(self, limit: int = 10) -> list[VouchEntry]:
        result = await self.session.execute(
            select(User.display_name, Order.product_name, Order.price, Order.created_at)
            .join(User, User.id == Order.user_id)
            .where(Order.status == OrderStatus.COMPLETED)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return [VouchEntry(*row) for row in result.all()]

    async def most_popular_product(self) -> tuple[str, int] | None:
        result = await self.session.execute(
            select(Order.product_name, func.count(Order.id).label("count"))
            .where(Order.status == OrderStatus.COMPLETED)
            .group_by(Order.product_name)
            .order_by(func.count(Order.id).desc())
            .limit(1)
        )
        row = result.first()
        return (row[0], row[1]) if row else None
