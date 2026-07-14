"""Balance view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService
from utils.banners import render_banner_message
from utils.formatting import format_price

router = Router(name="balance")


@router.callback_query(F.data == "menu:balance")
async def show_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    service = UserService(session)
    account = await service.get_profile(callback.from_user.id)

    text = f"<b>Balance</b>\n\nCurrent balance: {format_price(account.balance)}"

    builder = InlineKeyboardBuilder()
    builder.button(text="Deposit Funds", callback_data="menu:deposit")
    builder.button(text="Back to Menu", callback_data="menu:home")
    builder.adjust(1)

    if callback.message is not None:
        await render_banner_message(callback.message, "balance", text, builder.as_markup())
    await callback.answer()
