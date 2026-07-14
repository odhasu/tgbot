"""Static support-contact view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from utils.telegram import render_text_message

router = Router(name="support")


@router.callback_query(F.data == "menu:support")
async def show_support(callback: CallbackQuery) -> None:
    text = (
        "<b>Support</b>\n\n"
        f"Need help? Message {settings.support_contact} and we'll get back to you as soon as possible."
    )

    builder = InlineKeyboardBuilder()
    username = settings.support_contact.lstrip("@")
    builder.button(text="Message Support", url=f"https://t.me/{username}")
    builder.button(text="Back to Menu", callback_data="menu:home")
    builder.adjust(1)

    if callback.message is not None:
        await render_text_message(callback.message, text, builder.as_markup())
    await callback.answer()
