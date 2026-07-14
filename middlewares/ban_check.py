"""Blocks banned users from any further interaction with the bot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from repositories.user_repository import UserRepository

BANNED_TEXT = "You have been banned from using this bot."


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        session = data.get("session")
        if tg_user is not None and session is not None:
            user = await UserRepository(session).get_by_telegram_id(tg_user.id)
            if user is not None and user.is_banned:
                inner = event.event if isinstance(event, Update) else event
                if isinstance(inner, Message):
                    await inner.answer(BANNED_TEXT)
                elif isinstance(inner, CallbackQuery):
                    await inner.answer(BANNED_TEXT, show_alert=True)
                return None

        return await handler(event, data)
