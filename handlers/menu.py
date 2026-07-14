"""Main-menu navigation: return to the home screen from anywhere."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.main_menu import main_menu_keyboard
from services.user_service import UserService
from utils.banners import render_banner_message

router = Router(name="menu")


@router.callback_query(F.data == "menu:home")
async def handle_home(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_user = callback.from_user
    service = UserService(session)
    account = await service.get_profile(tg_user.id)

    if callback.message is not None:
        await render_banner_message(
            callback.message,
            "vex",
            f"Welcome back, {account.display_name}!\n\nUse the menu below.",
            main_menu_keyboard(account.is_admin),
        )
    await callback.answer()
