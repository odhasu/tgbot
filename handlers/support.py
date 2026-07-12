"""Static support-contact view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from config import settings
from keyboards.common import back_to_menu_keyboard

router = Router(name="support")


@router.callback_query(F.data == "menu:support")
async def show_support(callback: CallbackQuery) -> None:
    text = (
        "📞 <b>Support</b>\n\n"
        f"Need help? Contact {settings.support_contact} and we'll get back to you as soon as possible."
    )

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
