"""Browse categories/products and complete purchases."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import back_to_menu_keyboard
from keyboards.shop import (
    categories_keyboard,
    product_detail_keyboard,
    products_keyboard,
)
from services.exceptions import (
    CategoryNotFoundError,
    InsufficientBalanceError,
    OutOfStockError,
    ProductNotFoundError,
)
from services.order_service import OrderService
from services.shop_service import ShopService
from utils.banners import render_banner_message
from utils.formatting import format_price
from utils.pricing import WARRANTY_PRICE
from utils.telegram import render_product_message, render_text_message
from utils.logger import get_logger

logger = get_logger("shopbot.handlers.shop")

router = Router(name="shop")


@router.callback_query(F.data == "menu:shop")
async def show_categories(callback: CallbackQuery, session: AsyncSession) -> None:
    service = ShopService(session)
    categories = await service.list_categories(active_only=True)

    if not categories:
        text = "<b>Shop</b>\n\nNo categories available yet. Check back soon!"
        keyboard = back_to_menu_keyboard()
    else:
        text = "<b>Shop</b>\n\nChoose a category:"
        keyboard = categories_keyboard(categories)

    if callback.message is not None:
        await render_banner_message(callback.message, "shop", text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("shop:cat:"))
async def show_products(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[2])
    service = ShopService(session)

    try:
        category = await service.get_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("Category no longer exists.", show_alert=True)
        return

    products = await service.list_products(category_id, active_only=True)

    header = f"<b>{category.name}</b>"
    if category.description:
        header += f"\n{category.description}"

    if not products:
        text = f"{header}\n\nNo products in this category yet."
    else:
        text = f"{header}\n\nChoose a product:"

    if callback.message is not None:
        await render_text_message(callback.message, text, products_keyboard(products))
    await callback.answer()


@router.callback_query(F.data.startswith("shop:prod:"))
async def show_product(callback: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(callback.data.split(":")[2])
    service = ShopService(session)

    try:
        product = await service.get_product(product_id)
    except ProductNotFoundError:
        await callback.answer("Product no longer exists.", show_alert=True)
        return

    text = (
        f"<b>{product.name}</b>\n\n"
        f"{product.description}\n\n"
        f"Price: {format_price(product.price)}\n"
        f"Stock: {product.stock}\n\n"
        f"Warranty covers the product for its full subscription period, for an extra {format_price(WARRANTY_PRICE)}."
    )

    if callback.message is not None:
        await render_product_message(
            callback.message, text, product_detail_keyboard(product), product.photo_file_id
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:confirm:"))
async def execute_purchase(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, product_id_raw, with_warranty_raw = callback.data.split(":")
    product_id = int(product_id_raw)
    with_warranty = with_warranty_raw == "1"
    order_service = OrderService(session)
    tg_user = callback.from_user

    try:
        order = await order_service.purchase(tg_user.id, product_id, with_warranty=with_warranty)
    except InsufficientBalanceError:
        await callback.answer("Insufficient balance.", show_alert=True)
        return
    except OutOfStockError:
        await callback.answer("This product just went out of stock.", show_alert=True)
        return
    except ProductNotFoundError:
        await callback.answer("Product no longer exists.", show_alert=True)
        return

    text = (
        "<b>Purchase complete!</b>\n\n"
        f"Order #{order.id}\n"
        f"{order.product_name} — {format_price(order.price)}"
    )
    if order.has_warranty:
        text += "\nWarranty: Yes (full subscription period)"

    if callback.message is not None:
        await render_text_message(callback.message, text, back_to_menu_keyboard())
    await callback.answer("Purchase successful!")
