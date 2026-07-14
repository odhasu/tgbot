"""Main menu inline keyboard."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Shop", callback_data="menu:shop")
    builder.button(text="Balance", callback_data="menu:balance")
    builder.button(text="Profile", callback_data="menu:profile")
    builder.button(text="Support", callback_data="menu:support")
    if is_admin:
        builder.button(text="Admin", callback_data="menu:admin")
    builder.adjust(2)
    return builder.as_markup()
