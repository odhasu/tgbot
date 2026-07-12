"""Helpers for rendering messages that may switch between text and photo."""

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


async def render_text_message(message: Message, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    """Show `text`/`reply_markup`, replacing `message` even if it was a photo message."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.delete()
        await message.answer(text, reply_markup=reply_markup)


async def render_product_message(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    photo_file_id: str | None,
) -> None:
    """Show `text`/`reply_markup` as a photo caption or plain text, replacing `message`."""
    if photo_file_id:
        await message.delete()
        await message.answer_photo(photo_file_id, caption=text, reply_markup=reply_markup)
        return
    await render_text_message(message, text, reply_markup)
