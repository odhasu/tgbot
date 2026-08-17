"""Admin-only health and wallet view for the upstream buyer API."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.admin import back_to_admin_keyboard
from services.canboso_api import canboso_api
from services.exceptions import ProviderError
from utils.pricing import RETAIL_PRICE_MULTIPLIER
from utils.telegram import render_text_message

router = Router(name="admin_provider")


@router.callback_query(F.data == "admin:provider")
async def show_provider_status(callback: CallbackQuery) -> None:
    try:
        balance = await canboso_api.get_balance(force_refresh=True)
        products = await canboso_api.list_products()
    except ProviderError as exc:
        text = (
            "<b>Supplier API</b>\n\n"
            f"Connection error: {html.escape(str(exc))}\n\n"
            "Check the API key and supplier status."
        )
    else:
        in_stock = sum(product.availability.in_stock for product in products)
        text = (
            "<b>Supplier API</b>\n\n"
            "Connection: Online\n"
            f"Wholesale Wallet: {html.escape(balance.text)}\n"
            f"Catalog Products: {len(products)}\n"
            f"In Stock: {in_stock}\n"
            f"Retail Multiplier: {RETAIL_PRICE_MULTIPLIER.normalize()}×\n\n"
            "The wholesale wallet must cover an order before the customer can buy it."
        )
    if callback.message is not None:
        await render_text_message(callback.message, text, back_to_admin_keyboard())
    await callback.answer()
