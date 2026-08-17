"""Business logic for provider purchases and local order history."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import OrderStatus
from models.order import Order
from repositories.order_repository import OrderRepository, VouchEntry
from repositories.user_repository import UserRepository
from services.canboso_api import PurchaseResult, canboso_api
from services.exceptions import (
    InsufficientBalanceError,
    OrderNotFoundError,
    OutOfStockError,
    UserNotFoundError,
)
from utils.logger import get_logger
from utils.pricing import retail_price

logger = get_logger("shopbot.orders")
_purchase_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass(frozen=True, slots=True)
class CompletedPurchase:
    local_order: Order
    provider: PurchaseResult


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.users = UserRepository(session)

    async def purchase(
        self,
        telegram_id: int,
        product_id: str,
        *,
        quantity: int = 1,
        customer_email: str | None = None,
        slot_months: int | None = None,
        idempotency_key: str | None = None,
    ) -> CompletedPurchase:
        async with _purchase_locks[telegram_id]:
            user = await self.users.get_by_telegram_id(telegram_id)
            if user is None:
                raise UserNotFoundError(f"No user with telegram_id={telegram_id}")

            product = await canboso_api.get_product(product_id)
            if not product.availability.in_stock:
                raise OutOfStockError(f"Product {product.name!r} is out of stock")
            if quantity < 1:
                raise ValueError("quantity must be positive")
            if product.requirements.quantity_fixed is not None:
                quantity = product.requirements.quantity_fixed
            if product.availability.available is not None and quantity > product.availability.available:
                raise OutOfStockError(f"Only {product.availability.available} item(s) remain")

            estimated_units = Decimal(quantity)
            if product.requirements.slot_months and slot_months is not None:
                estimated_units *= Decimal(slot_months)
            estimated_total = retail_price(
                product.price.amount * estimated_units, product.price.currency
            )
            if user.balance < estimated_total:
                raise InsufficientBalanceError(
                    f"Balance {user.balance} is less than estimated retail price {estimated_total}"
                )

            result = await canboso_api.purchase(
                product_id,
                quantity=quantity,
                customer_email=customer_email,
                slot_months=slot_months,
                idempotency_key=idempotency_key,
            )

            existing = await self.orders.get_by_provider_order_code(result.order.code)
            if existing is not None:
                return CompletedPurchase(existing, result)

            retail_total = retail_price(result.payment.amount, result.payment.currency)
            if retail_total > user.balance:
                logger.error(
                    "Provider charged more than quoted: telegram_id=%s provider_order=%s "
                    "customer_balance=%s retail_total=%s",
                    telegram_id,
                    result.order.code,
                    user.balance,
                    retail_total,
                )

            status = (
                OrderStatus.COMPLETED
                if result.order.status.lower() == "completed"
                else OrderStatus.PENDING
            )
            await self.users.register_purchase(user, retail_total)
            order = await self.orders.create(
                user_id=user.id,
                product_id=None,
                product_name=result.order.product_name,
                price=retail_total,
                provider_cost=result.payment.amount,
                status=status,
                currency=result.payment.currency,
                provider_order_code=result.order.code,
                provider_product_id=result.order.product_id,
                fulfillment_status=result.order.fulfillment_status,
                quantity=result.order.quantity,
                bonus_quantity=result.order.bonus_quantity,
                final_quantity=result.order.final_quantity,
            )
            await self.session.commit()

        logger.info(
            "Provider purchase recorded: user_id=%s telegram_id=%s provider_order=%s "
            "product_id=%s amount=%s currency=%s status=%s",
            user.id,
            telegram_id,
            result.order.code,
            result.order.product_id,
            retail_total,
            result.payment.currency,
            result.order.status,
        )
        return CompletedPurchase(order, result)

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
            "Local order status changed by admin %s: order_id=%s status=%s",
            actor_telegram_id,
            order_id,
            status.value,
        )
        return order
