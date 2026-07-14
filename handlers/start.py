"""Entry point handler: registers/loads the user and shows the main menu."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.main_menu import main_menu_keyboard
from services.settings_service import SettingsService
from services.user_service import UserService
from utils.banners import BANNER_FILES

router = Router(name="start")


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

    welcome_text = await SettingsService(session).get_welcome_text()
    await message.answer_photo(
        FSInputFile(BANNER_FILES["vex"]),
        caption=welcome_text.replace("{name}", account.display_name),
        reply_markup=main_menu_keyboard(account.is_admin),
    )
