"""Inline keyboards for the Canboso-backed storefront."""

from __future__ import annotations

from collections import Counter

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.canboso_api import ProviderProduct
from utils.formatting import format_money
from utils.pricing import retail_price

PRODUCTS_PER_PAGE = 8

TYPE_LABELS = {
    "account": "Accounts & Keys",
    "slot": "Slots",
    "upgrade_account": "Account Upgrades",
}


def _short_label(value: str, limit: int = 44) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else f"{value[: limit - 1]}…"


def product_types_keyboard(products: tuple[ProviderProduct, ...]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    counts = Counter(product.product_type for product in products)
    for product_type in ("account", "slot", "upgrade_account"):
        count = counts.get(product_type, 0)
        if count:
            builder.button(
                text=f"{TYPE_LABELS[product_type]} ({count})",
                callback_data=f"shop:type:{product_type}:0",
            )
    builder.button(text="Back to Menu", callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def products_keyboard(
    products: tuple[ProviderProduct, ...], product_type: str, page: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_count = max(1, (len(products) + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE)
    page = max(0, min(page, page_count - 1))
    start = page * PRODUCTS_PER_PAGE
    for product in products[start : start + PRODUCTS_PER_PAGE]:
        stock = "" if product.availability.in_stock else " [sold out]"
        label = _short_label(f"{product.name}{stock}", 46)
        builder.button(
            text=f"{label} — {format_money(retail_price(product.price.amount, product.price.currency), product.price.currency)}",
            callback_data=f"shop:prod:{product.id}:1",
        )
    if page > 0:
        builder.button(text="Previous", callback_data=f"shop:type:{product_type}:{page - 1}")
    if page + 1 < page_count:
        builder.button(text="Next", callback_data=f"shop:type:{product_type}:{page + 1}")
    builder.button(text=f"Page {page + 1}/{page_count}", callback_data="shop:noop")
    builder.button(text="Back to Product Types", callback_data="menu:shop")
    builder.adjust(*([1] * min(PRODUCTS_PER_PAGE, len(products[start : start + PRODUCTS_PER_PAGE]))), 2, 1, 1)
    return builder.as_markup()


def product_detail_keyboard(product: ProviderProduct, quantity: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fixed_quantity = product.requirements.quantity_fixed
    if fixed_quantity is None and product.availability.in_stock:
        builder.button(text="−10", callback_data=f"shop:qty:{product.id}:{quantity - 10}")
        builder.button(text="−1", callback_data=f"shop:qty:{product.id}:{quantity - 1}")
        builder.button(text=f"Qty: {quantity}", callback_data="shop:noop")
        builder.button(text="+1", callback_data=f"shop:qty:{product.id}:{quantity + 1}")
        builder.button(text="+10", callback_data=f"shop:qty:{product.id}:{quantity + 10}")
    if product.availability.in_stock:
        builder.button(text="Continue to Purchase", callback_data=f"shop:buy:{product.id}:{quantity}")
    builder.button(
        text="Back",
        callback_data=f"shop:type:{product.product_type}:0",
    )
    builder.adjust(5, 1, 1)
    return builder.as_markup()


def months_keyboard(product: ProviderProduct, quantity: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for months in product.requirements.allowed_months:
        builder.button(
            text=f"{months} month{'s' if months != 1 else ''}",
            callback_data=f"shop:month:{product.id}:{quantity}:{months}",
        )
    builder.button(text="Cancel", callback_data=f"shop:prod:{product.id}:{quantity}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_purchase_keyboard(
    product_id: str, quantity: int, slot_months: int | None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    months = slot_months or 0
    builder.button(
        text="Confirm & Pay",
        callback_data=f"shop:confirm:{product_id}:{quantity}:{months}",
    )
    builder.button(text="Cancel", callback_data=f"shop:prod:{product_id}:{quantity}")
    builder.adjust(1)
    return builder.as_markup()


def purchase_cancel_keyboard(product: ProviderProduct, quantity: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Cancel", callback_data=f"shop:prod:{product.id}:{quantity}")
    return builder.as_markup()
