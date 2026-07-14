"""Crypto deposit keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.crypto import CRYPTO_LABELS


def deposit_coins_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for coin, label in CRYPTO_LABELS.items():
        builder.button(text=label, callback_data=f"deposit:coin:{coin}")
    builder.button(text="Back to Balance", callback_data="menu:balance")
    builder.adjust(2)
    return builder.as_markup()


def deposit_address_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Back", callback_data="menu:deposit")
    return builder.as_markup()
