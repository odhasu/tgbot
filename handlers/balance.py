"""Balance view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from keyboards.common import back_to_menu_keyboard
from services.user_service import UserService
from utils.formatting import format_price

router = Router(name="balance")


@router.callback_query(F.data == "menu:balance")
async def show_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    service = UserService(session)
    account = await service.get_profile(callback.from_user.id)

    text = (
        "💰 <b>Balance</b>\n\n"
        f"Current balance: {format_price(account.balance)}\n\n"
        f"To top up, contact {settings.support_contact}."
    )

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
