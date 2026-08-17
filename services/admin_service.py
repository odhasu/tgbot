"""Business logic for admin-only operations: stats and broadcast targeting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.order_repository import OrderRepository
from repositories.user_repository import UserRepository
from utils.logger import get_logger

logger = get_logger("shopbot.admin")


@dataclass(frozen=True, slots=True)
class ShopStats:
    total_users: int
    total_orders: int
    revenue: Decimal
    provider_cost: Decimal
    gross_profit: Decimal
    products_sold: int
    most_popular_product: str | None


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.orders = OrderRepository(session)

    async def get_stats(self) -> ShopStats:
        popular = await self.orders.most_popular_product()
        revenue = await self.orders.total_revenue()
        provider_cost = await self.orders.total_provider_cost()
        return ShopStats(
            total_users=await self.users.count(),
            total_orders=await self.orders.count(),
            revenue=revenue,
            provider_cost=provider_cost,
            gross_profit=revenue - provider_cost,
            products_sold=await self.orders.total_products_delivered(),
            most_popular_product=popular[0] if popular else None,
        )

    async def get_broadcast_targets(self) -> list[int]:
        """Return telegram_ids of all registered users."""
        users = await self.users.list_all(limit=1_000_000)
        return [user.telegram_id for user in users]

    def log_broadcast(self, actor_telegram_id: int, recipient_count: int, message_preview: str) -> None:
        logger.info(
            "Broadcast sent by admin %s to %s users: %r",
            actor_telegram_id,
            recipient_count,
            message_preview[:80],
        )
