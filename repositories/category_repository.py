"""Data access for Category records."""

from __future__ import annotations

from sqlalchemy import select

from models.category import Category
from repositories.base import BaseRepository


class CategoryRepository(BaseRepository):
    async def get_by_id(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)

    async def get_by_name(self, name: str) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Category]:
        result = await self.session.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.name)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Category]:
        result = await self.session.execute(
            select(Category).order_by(Category.sort_order, Category.name)
        )
        return list(result.scalars().all())

    async def create(self, name: str, description: str | None = None, sort_order: int = 0) -> Category:
        category = Category(name=name, description=description, sort_order=sort_order)
        self.session.add(category)
        await self.session.flush()
        return category

    async def update(self, category: Category, **fields: object) -> Category:
        for key, value in fields.items():
            setattr(category, key, value)
        await self.session.flush()
        return category

    async def set_active(self, category: Category, is_active: bool) -> Category:
        category.is_active = is_active
        await self.session.flush()
        return category

    async def delete(self, category: Category) -> None:
        await self.session.delete(category)
        await self.session.flush()
