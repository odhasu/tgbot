"""Business logic for purchases and order history."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import OrderStatus
from models.order import Order
from repositories.order_repository import OrderRepository, VouchEntry
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from services.exceptions import (
    InsufficientBalanceError,
    OrderNotFoundError,
    OutOfStockError,
    ProductNotFoundError,
    UserNotFoundError,
)
from utils.logger import get_logger
from utils.pricing import WARRANTY_PRICE

logger = get_logger("shopbot.orders")


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)
        self.users = UserRepository(session)

    async def purchase(self, telegram_id: int, product_id: int, with_warranty: bool = False) -> Order:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"No user with telegram_id={telegram_id}")

        product = await self.products.get_by_id(product_id)
        if product is None or not product.is_active:
            raise ProductNotFoundError(f"No active product with id={product_id}")

        if product.stock <= 0:
            raise OutOfStockError(f"Product {product.name!r} is out of stock")

        total_price = product.price + (WARRANTY_PRICE if with_warranty else Decimal("0"))

        if user.balance < total_price:
            raise InsufficientBalanceError(
                f"Balance {user.balance} is less than price {total_price}"
            )

        await self.users.register_purchase(user, total_price)
        await self.products.decrement_stock(product)
        order = await self.orders.create(
            user_id=user.id,
            product_id=product.id,
            product_name=product.name,
            price=total_price,
            has_warranty=with_warranty,
        )
        await self.session.commit()

        logger.info(
            "Purchase completed: user_id=%s telegram_id=%s product_id=%s price=%s warranty=%s order_id=%s",
            user.id,
            telegram_id,
            product.id,
            total_price,
            with_warranty,
            order.id,
        )
        return order

    async def list_user_orders(self, telegram_id: int) -> list[Order]:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"No user with telegram_id={telegram_id}")
        return await self.orders.list_by_user(user.id)

    async def list_all_orders(self, limit: int = 50, offset: int = 0) -> list[Order]:
        return await self.orders.list_all(limit=limit, offset=offset)

    async def list_recent_vouches(self, limit: int = 10) -> list[VouchEntry]:
        return await self.orders.list_recent_vouches(limit=limit)

    async def get_order(self, order_id: int) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(f"No order with id={order_id}")
        return order

    async def update_status(self, order_id: int, status: OrderStatus, actor_telegram_id: int) -> Order:
        order = await self.get_order(order_id)
        await self.orders.update_status(order, status)
        await self.session.commit()
        logger.info(
            "Order status changed by admin %s: order_id=%s status=%s",
            actor_telegram_id,
            order_id,
            status.value,
        )
        return order
