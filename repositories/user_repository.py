"""Data access for User records."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: str | None,
        display_name: str,
        is_admin: bool = False,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
            is_admin=is_admin,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_profile(self, user: User, username: str | None, display_name: str) -> User:
        user.username = username
        user.display_name = display_name
        await self.session.flush()
        return user

    async def adjust_balance(self, user: User, delta: Decimal) -> User:
        user.balance = user.balance + delta
        await self.session.flush()
        return user

    async def register_purchase(self, user: User, amount: Decimal) -> User:
        user.balance = user.balance - amount
        user.total_spent = user.total_spent + amount
        user.total_orders = user.total_orders + 1
        await self.session.flush()
        return user

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(User.joined_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def search(self, query: str, limit: int = 20) -> list[User]:
        pattern = f"%{query}%"
        conditions = [User.username.ilike(pattern), User.display_name.ilike(pattern)]
        if query.isdigit():
            conditions.append(User.telegram_id == int(query))
        result = await self.session.execute(select(User).where(or_(*conditions)).limit(limit))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()
