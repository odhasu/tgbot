"""Business logic for categories and products."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.enums import DeliveryType
from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from services.exceptions import (
    CategoryAlreadyExistsError,
    CategoryNotFoundError,
    ProductNotFoundError,
)
from utils.logger import get_logger

logger = get_logger("shopbot.shop")


class ShopService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)

    # --- Categories -----------------------------------------------------

    async def list_categories(self, active_only: bool = True) -> list[Category]:
        if active_only:
            return await self.categories.list_active()
        return await self.categories.list_all()

    async def get_category(self, category_id: int) -> Category:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError(f"No category with id={category_id}")
        return category

    async def create_category(self, name: str) -> Category:
        existing = await self.categories.get_by_name(name)
        if existing is not None:
            raise CategoryAlreadyExistsError(f"Category {name!r} already exists")

        category = await self.categories.create(name)
        await self.session.commit()
        logger.info("Category created: %s", name)
        return category

    async def delete_category(self, category_id: int) -> None:
        category = await self.get_category(category_id)
        await self.categories.delete(category)
        await self.session.commit()
        logger.info("Category deleted: id=%s name=%s", category_id, category.name)

    # --- Products ---------------------------------------------------------

    async def list_products(self, category_id: int, active_only: bool = True) -> list[Product]:
        return await self.products.list_by_category(category_id, active_only=active_only)

    async def list_all_products(self) -> list[Product]:
        return await self.products.list_all()

    async def get_product(self, product_id: int) -> Product:
        product = await self.products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(f"No product with id={product_id}")
        return product

    async def create_product(
        self,
        category_id: int,
        name: str,
        description: str,
        price: Decimal,
        stock: int,
        delivery_type: DeliveryType,
        photo_file_id: str | None = None,
    ) -> Product:
        await self.get_category(category_id)
        product = await self.products.create(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            stock=stock,
            delivery_type=delivery_type,
            photo_file_id=photo_file_id,
        )
        await self.session.commit()
        logger.info("Product created: id=%s name=%s", product.id, name)
        return product

    async def update_product(self, product_id: int, **fields: object) -> Product:
        product = await self.get_product(product_id)
        await self.products.update(product, **fields)
        await self.session.commit()
        logger.info("Product updated: id=%s fields=%s", product_id, list(fields))
        return product

    async def delete_product(self, product_id: int) -> None:
        product = await self.get_product(product_id)
        await self.products.delete(product)
        await self.session.commit()
        logger.info("Product deleted: id=%s name=%s", product_id, product.name)

    async def count_active_products(self) -> int:
        return await self.products.count_active()
