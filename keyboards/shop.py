"""Inline keyboards for browsing and buying products."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.category import Category
from models.product import Product
from utils.formatting import format_price


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=f"shop:cat:{category.id}")
    builder.button(text="⬅️ Back to Menu", callback_data="menu:home")
    builder.adjust(2)
    return builder.as_markup()


def products_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        label = f"{product.name} — {format_price(product.price)}"
        builder.button(text=label, callback_data=f"shop:prod:{product.id}")
    builder.button(text="⬅️ Back to Categories", callback_data="menu:shop")
    builder.adjust(1)
    return builder.as_markup()


def product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Buy", callback_data=f"shop:buy:{product.id}")
    builder.button(text="⬅️ Back", callback_data=f"shop:cat:{product.category_id}")
    builder.adjust(1)
    return builder.as_markup()


def purchase_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm", callback_data=f"shop:confirm:{product_id}")
    builder.button(text="❌ Cancel", callback_data=f"shop:prod:{product_id}")
    builder.adjust(2)
    return builder.as_markup()
