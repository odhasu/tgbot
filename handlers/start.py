"""Entry point handler: registers/loads the user and shows the main menu."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.main_menu import main_menu_keyboard
from services.user_service import UserService

router = Router(name="start")

WELCOME_TEXT = (
    "👋 Welcome to the Shop, {name}!\n\n"
    "Use the menu below to browse products, manage your balance, and more."
)


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return

    service = UserService(session)
    account, _created = await service.get_or_create_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        display_name=tg_user.full_name,
    )

    await message.answer(
        WELCOME_TEXT.format(name=account.display_name),
        reply_markup=main_menu_keyboard(account.is_admin),
    )
