"""Business logic for user accounts."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.user import User
from repositories.user_repository import UserRepository
from services.exceptions import UserNotFoundError
from utils.logger import get_logger

logger = get_logger("shopbot.users")


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def get_or_create_user(
        self, telegram_id: int, username: str | None, display_name: str
    ) -> tuple[User, bool]:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is not None:
            should_be_admin = settings.is_admin(telegram_id)
            profile_changed = user.username != username or user.display_name != display_name
            admin_changed = user.is_admin != should_be_admin
            if profile_changed:
                await self.users.update_profile(user, username, display_name)
            if admin_changed:
                user.is_admin = should_be_admin
            if profile_changed or admin_changed:
                await self.session.commit()
            return user, False

        user = await self.users.create(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
            is_admin=settings.is_admin(telegram_id),
        )
        await self.session.commit()
        logger.info("New user registered: telegram_id=%s username=%s", telegram_id, username)
        return user, True

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.users.get_by_id(user_id)

    async def get_profile(self, telegram_id: int) -> User:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"No user with telegram_id={telegram_id}")
        return user

    async def adjust_balance(self, user_id: int, delta: Decimal, actor_telegram_id: int) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"No user with id={user_id}")

        await self.users.adjust_balance(user, delta)
        await self.session.commit()
        logger.info(
            "Balance adjusted by admin %s: user_id=%s delta=%s new_balance=%s",
            actor_telegram_id,
            user_id,
            delta,
            user.balance,
        )
        return user

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[User]:
        return await self.users.list_all(limit=limit, offset=offset)

    async def search_users(self, query: str) -> list[User]:
        return await self.users.search(query)

    async def count_users(self) -> int:
        return await self.users.count()
