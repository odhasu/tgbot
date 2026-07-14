"""Idempotent startup seed: ensures the default catalog exists on any fresh/wiped database."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import DeliveryType
from repositories.setting_repository import SettingRepository
from services.shop_service import ShopService
from utils.logger import get_logger

logger = get_logger("shopbot.seed")

PRICE_INCREASE_KEY = "price_increase_10_applied"
PRICE_INCREASE = Decimal("10")

CATEGORIES = ["Claude", "ChatGPT"]

PRODUCTS = [
    ("Claude", "Claude Max 20x - 1 Year", Decimal("90"), 11),
    ("Claude", "Claude Max 20x - 1 Month", Decimal("30"), 18),
    ("Claude", "Claude Max 5x - 1 Year", Decimal("40"), 17),
    ("Claude", "Claude Max 5x - 3 Month", Decimal("20"), 23),
    ("ChatGPT", "ChatGPT Plus - 1 Year", Decimal("25"), 147),
    ("ChatGPT", "ChatGPT Pro 20x - 6 Month", Decimal("50"), 42),
    ("ChatGPT", "ChatGPT Pro 20x - 1 Year", Decimal("80"), 8),
]


async def seed_default_catalog(session: AsyncSession) -> None:
    """Create the default categories/products only if the catalog is empty."""
    service = ShopService(session)
    existing = await service.list_categories(active_only=False)
    if existing:
        return

    logger.info("Empty catalog detected, seeding default categories/products")
    category_ids: dict[str, int] = {}
    for name in CATEGORIES:
        category = await service.create_category(name)
        category_ids[name] = category.id

    for category_name, product_name, price, stock in PRODUCTS:
        await service.create_product(
            category_id=category_ids[category_name],
            name=product_name,
            description=product_name,
            price=price,
            stock=stock,
            delivery_type=DeliveryType.MANUAL,
        )
    logger.info("Seeded %d categories and %d products", len(CATEGORIES), len(PRODUCTS))


async def apply_price_increase_once(session: AsyncSession) -> None:
    """One-time +$10 bump to every product's price. Runs once per database, ever."""
    settings = SettingRepository(session)
    if await settings.get(PRICE_INCREASE_KEY) is not None:
        return

    service = ShopService(session)
    products = await service.list_all_products()
    for product in products:
        await service.update_product(product.id, price=product.price + PRICE_INCREASE)

    await settings.set(PRICE_INCREASE_KEY, "true")
    await session.commit()
    logger.info("Applied one-time +$%s price increase to %d products", PRICE_INCREASE, len(products))
