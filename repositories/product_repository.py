"""Data access for Product records."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from models.enums import DeliveryType
from models.product import Product
from repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def list_by_category(self, category_id: int, active_only: bool = True) -> list[Product]:
        stmt = select(Product).where(Product.category_id == category_id)
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(Product.name))
        return list(result.scalars().all())

    async def list_all(self) -> list[Product]:
        result = await self.session.execute(select(Product).order_by(Product.id.desc()))
        return list(result.scalars().all())

    async def create(
        self,
        category_id: int,
        name: str,
        description: str,
        price: Decimal,
        stock: int,
        delivery_type: DeliveryType,
        photo_file_id: str | None = None,
    ) -> Product:
        product = Product(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            stock=stock,
            delivery_type=delivery_type,
            photo_file_id=photo_file_id,
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def update(self, product: Product, **fields: object) -> Product:
        for key, value in fields.items():
            setattr(product, key, value)
        await self.session.flush()
        return product

    async def decrement_stock(self, product: Product, quantity: int = 1) -> Product:
        product.stock = max(product.stock - quantity, 0)
        await self.session.flush()
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.flush()

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        )
        return result.scalar_one()
