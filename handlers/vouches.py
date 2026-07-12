"""Recent-purchases feed, shown as social proof."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import back_to_menu_keyboard
from services.order_service import OrderService
from utils.formatting import format_price

router = Router(name="vouches")


@router.callback_query(F.data == "menu:vouches")
async def show_vouches(callback: CallbackQuery, session: AsyncSession) -> None:
    service = OrderService(session)
    vouches = await service.list_recent_vouches(limit=10)

    if not vouches:
        text = "⭐ <b>Vouches</b>\n\nNo purchases yet — be the first!"
    else:
        lines = ["⭐ <b>Recent Vouches</b>\n"]
        for vouch in vouches:
            date = vouch.created_at.strftime("%Y-%m-%d")
            lines.append(f"✅ {vouch.buyer_name} bought {vouch.product_name} — {format_price(vouch.price)} ({date})")
        text = "\n".join(lines)

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
