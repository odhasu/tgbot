"""Profile view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import back_to_menu_keyboard
from services.user_service import UserService
from utils.formatting import format_price

router = Router(name="profile")


@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    service = UserService(session)
    account = await service.get_profile(callback.from_user.id)

    username = f"@{account.username}" if account.username else "—"
    joined = account.joined_at.strftime("%Y-%m-%d")

    text = (
        "👤 <b>Profile</b>\n\n"
        f"Name: {account.display_name}\n"
        f"Username: {username}\n"
        f"Balance: {format_price(account.balance)}\n"
        f"Total Orders: {account.total_orders}\n"
        f"Total Spent: {format_price(account.total_spent)}\n"
        f"Member Since: {joined}"
    )

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
