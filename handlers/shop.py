"""Browse and purchase the live Canboso catalog at the configured retail markup."""

from __future__ import annotations

import html
import re
import uuid
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from keyboards.shop import (
    TYPE_LABELS,
    confirm_purchase_keyboard,
    months_keyboard,
    product_detail_keyboard,
    product_types_keyboard,
    products_keyboard,
    purchase_cancel_keyboard,
)
from keyboards.common import back_to_menu_keyboard
from services.canboso_api import ProviderProduct, PurchaseResult, canboso_api
from services.exceptions import (
    InsufficientBalanceError,
    OutOfStockError,
    ProductNotFoundError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderPurchaseError,
    ProviderRateLimitError,
)
from services.order_service import OrderService
from services.user_service import UserService
from states.shop_states import PurchaseStates
from utils.banners import render_banner_message
from utils.formatting import format_money
from utils.logger import get_logger
from utils.pricing import retail_price
from utils.telegram import render_product_message, render_text_message

logger = get_logger("shopbot.handlers.shop")
router = Router(name="shop")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
EMPTY_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[])


def _retail_unit(product: ProviderProduct) -> Decimal:
    return retail_price(product.price.amount, product.price.currency)


def _estimated_total(
    product: ProviderProduct, quantity: int, slot_months: int | None = None
) -> Decimal:
    units = Decimal(quantity)
    if product.requirements.slot_months and slot_months is not None:
        units *= Decimal(slot_months)
    return retail_price(product.price.amount * units, product.price.currency)


def _stock_text(product: ProviderProduct) -> str:
    available = product.availability.available
    if available is None:
        return "Available"
    if available <= 0:
        return "Sold out"
    return f"{available} available"


def _promotion_lines(product: ProviderProduct) -> list[str]:
    lines: list[str] = []
    for promotion in product.promotions:
        if promotion.min_quantity is None:
            continue
        detail = f"Bulk offer from {promotion.min_quantity} items"
        if promotion.percent is not None:
            detail += f": {promotion.percent.normalize()}% off"
        if promotion.bonus_quantity is not None:
            detail += f": +{promotion.bonus_quantity} free"
        lines.append(detail)
    return lines


def _product_text(product: ProviderProduct, quantity: int) -> str:
    description_limit = 620 if product.image_url else 2600
    description = product.description.strip()
    if len(description) > description_limit:
        description = f"{description[: description_limit - 1].rstrip()}…"
    total = _estimated_total(product, quantity)
    lines = [
        f"<b>{html.escape(product.name)}</b>",
        "",
        html.escape(description) if description else "No description provided.",
        "",
        f"Retail price: {html.escape(format_money(_retail_unit(product), product.price.currency))}",
        f"Quantity: {quantity}",
        f"Estimated total: {html.escape(format_money(total, product.price.currency))}",
        f"Stock: {html.escape(_stock_text(product))}",
    ]
    promotions = _promotion_lines(product)
    if promotions:
        lines.extend(["", "<b>Offers</b>", *(html.escape(line) for line in promotions)])
    if product.requirements.customer_email:
        lines.extend(["", "Your email will be requested before payment."])
    return "\n".join(lines)


def _provider_message(exc: ProviderError) -> str:
    if isinstance(exc, ProviderRateLimitError):
        if exc.retry_after:
            return f"The catalog is busy. Please try again in {exc.retry_after} seconds."
        return "The catalog is busy. Please try again shortly."
    if isinstance(exc, ProviderAuthenticationError):
        return "Purchases are temporarily unavailable. Please contact support."
    if isinstance(exc, ProviderPurchaseError):
        message = str(exc)
        if "balance" in message.lower():
            return "Purchases are temporarily unavailable. Please contact support."
        return message[:180]
    return "The shop catalog is temporarily unavailable. Please try again shortly."


async def _get_product(callback: CallbackQuery, product_id: str) -> ProviderProduct | None:
    if not settings.catalog_enabled:
        await callback.answer("Products are temporarily unavailable.", show_alert=True)
        return None
    try:
        return await canboso_api.get_product(product_id)
    except ProductNotFoundError:
        await callback.answer("Product no longer exists.", show_alert=True)
    except ProviderError as exc:
        await callback.answer(_provider_message(exc), show_alert=True)
    return None


async def _show_confirmation(
    *,
    state: FSMContext,
    product: ProviderProduct,
    quantity: int,
    customer_email: str | None,
    slot_months: int | None,
    message: Message,
) -> None:
    idempotency_key = f"tg-{message.chat.id}-{uuid.uuid4().hex}"
    await state.set_state(PurchaseStates.confirmation)
    await state.update_data(
        product_id=product.id,
        quantity=quantity,
        customer_email=customer_email,
        slot_months=slot_months,
        idempotency_key=idempotency_key,
    )
    total = _estimated_total(product, quantity, slot_months)
    details = [
        "<b>Confirm Purchase</b>",
        "",
        html.escape(product.name),
        f"Quantity: {quantity}",
    ]
    if slot_months is not None:
        details.append(f"Duration: {slot_months} month{'s' if slot_months != 1 else ''}")
    if customer_email:
        details.append(f"Email: {html.escape(customer_email)}")
    details.extend(
        [
            f"Total: {html.escape(format_money(total, product.price.currency))}",
            "",
            "Your shop wallet will be charged after you confirm.",
        ]
    )
    await render_text_message(
        message,
        "\n".join(details),
        confirm_purchase_keyboard(product.id, quantity, slot_months),
    )


@router.callback_query(F.data == "shop:noop")
async def ignore_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "menu:shop")
async def show_product_types(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if not settings.catalog_enabled:
        if callback.message is not None:
            await render_banner_message(
                callback.message,
                "shop",
                "<b>Shop</b>\n\nNo products are available right now. Please check back soon.",
                back_to_menu_keyboard(),
            )
        await callback.answer()
        return
    try:
        products = await canboso_api.list_products()
    except ProviderError as exc:
        await callback.answer(_provider_message(exc), show_alert=True)
        return

    text = (
        "<b>Shop</b>\n\n"
        "Browse the live catalog and choose a product type.\n\n"
        "Choose a product type:"
    )
    if callback.message is not None:
        await render_banner_message(
            callback.message, "shop", text, product_types_keyboard(products)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:type:"))
async def show_products(callback: CallbackQuery) -> None:
    if not settings.catalog_enabled:
        await callback.answer("Products are temporarily unavailable.", show_alert=True)
        return
    _, _, product_type, page_raw = callback.data.split(":")
    try:
        all_products = await canboso_api.list_products()
    except ProviderError as exc:
        await callback.answer(_provider_message(exc), show_alert=True)
        return
    products = tuple(product for product in all_products if product.product_type == product_type)
    page = max(0, int(page_raw))
    label = TYPE_LABELS.get(product_type, "Products")
    text = f"<b>{html.escape(label)}</b>\n\nChoose a live product:"
    if callback.message is not None:
        await render_text_message(
            callback.message, text, products_keyboard(products, product_type, page)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:prod:"))
@router.callback_query(F.data.startswith("shop:qty:"))
async def show_product(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    _, _, product_id, quantity_raw = callback.data.split(":")
    product = await _get_product(callback, product_id)
    if product is None:
        return

    quantity = max(1, int(quantity_raw))
    if product.requirements.quantity_fixed is not None:
        quantity = product.requirements.quantity_fixed
    if product.availability.available is not None and product.availability.available > 0:
        quantity = min(quantity, product.availability.available)
    quantity = min(quantity, 1000)

    if callback.message is not None:
        text = _product_text(product, quantity)
        await render_product_message(
            callback.message,
            text,
            product_detail_keyboard(product, quantity),
            product.image_url if len(text) <= 950 else None,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:buy:"))
async def start_purchase(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, product_id, quantity_raw = callback.data.split(":")
    product = await _get_product(callback, product_id)
    if product is None:
        return
    if not product.availability.in_stock:
        await callback.answer("This product is sold out.", show_alert=True)
        return
    quantity = max(1, int(quantity_raw))
    if product.requirements.quantity_fixed is not None:
        quantity = product.requirements.quantity_fixed

    if product.requirements.slot_months:
        if not product.requirements.allowed_months:
            await callback.answer("No subscription durations are available.", show_alert=True)
            return
        if callback.message is not None:
            await render_text_message(
                callback.message,
                f"<b>{html.escape(product.name)}</b>\n\nChoose a subscription duration:",
                months_keyboard(product, quantity),
            )
        await callback.answer()
        return

    if product.requirements.customer_email:
        await state.set_state(PurchaseStates.customer_email)
        await state.update_data(product_id=product.id, quantity=quantity, slot_months=None)
        if callback.message is not None:
            await render_text_message(
                callback.message,
                f"<b>{html.escape(product.name)}</b>\n\nSend the email address to use for this order:",
                purchase_cancel_keyboard(product, quantity),
            )
        await callback.answer()
        return

    if callback.message is not None:
        await _show_confirmation(
            state=state,
            product=product,
            quantity=quantity,
            customer_email=None,
            slot_months=None,
            message=callback.message,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:month:"))
async def choose_month(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, product_id, quantity_raw, months_raw = callback.data.split(":")
    product = await _get_product(callback, product_id)
    if product is None:
        return
    quantity = int(quantity_raw)
    months = int(months_raw)
    if months not in product.requirements.allowed_months:
        await callback.answer("That duration is no longer available.", show_alert=True)
        return
    if product.requirements.customer_email:
        await state.set_state(PurchaseStates.customer_email)
        await state.update_data(product_id=product.id, quantity=quantity, slot_months=months)
        if callback.message is not None:
            await render_text_message(
                callback.message,
                f"<b>{html.escape(product.name)}</b>\n\nSend the email address to use for this order:",
                purchase_cancel_keyboard(product, quantity),
            )
    elif callback.message is not None:
        await _show_confirmation(
            state=state,
            product=product,
            quantity=quantity,
            customer_email=None,
            slot_months=months,
            message=callback.message,
        )
    await callback.answer()


@router.message(PurchaseStates.customer_email)
async def receive_customer_email(message: Message, state: FSMContext) -> None:
    if not settings.catalog_enabled:
        await state.clear()
        await message.answer("Products are temporarily unavailable.")
        return
    email = (message.text or "").strip()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        await message.answer("Send a valid email address, for example name@example.com.")
        return
    data = await state.get_data()
    try:
        product = await canboso_api.get_product(str(data["product_id"]))
    except (KeyError, ProductNotFoundError):
        await state.clear()
        await message.answer("This product is no longer available. Please reopen the shop.")
        return
    except ProviderError as exc:
        await message.answer(_provider_message(exc))
        return
    await _show_confirmation(
        state=state,
        product=product,
        quantity=int(data["quantity"]),
        customer_email=email,
        slot_months=data.get("slot_months"),
        message=message,
    )


def _purchase_summary(result: PurchaseResult, retail_total: Decimal, currency: str) -> str:
    order = result.order
    lines = [
        "<b>Purchase Complete</b>",
        "",
        f"Order: <code>{html.escape(order.code)}</code>",
        f"Product: {html.escape(order.product_name)}",
        f"Quantity delivered: {order.final_quantity}",
        f"Paid: {html.escape(format_money(retail_total, currency))}",
        f"Status: {html.escape(order.status)}",
    ]
    if order.fulfillment_status:
        lines.append(f"Fulfillment: {html.escape(order.fulfillment_status)}")
    if not result.accounts:
        lines.extend(
            [
                "",
                "No instant account details were returned. Keep the order code above for support and fulfillment.",
            ]
        )
    return "\n".join(lines)


def _delivery_messages(result: PurchaseResult) -> list[str]:
    blocks: list[str] = []
    for index, account in enumerate(result.accounts, start=1):
        fields = [f"Account {index}", f"User: {account.user}", f"Password: {account.password}"]
        if account.verify_email:
            fields.append(f"Verify email: {account.verify_email}")
        if account.expiry_text:
            fields.append(f"Expiry: {account.expiry_text}")
        if account.other_info:
            fields.append(f"Info: {account.other_info}")
        blocks.append(f"<pre>{html.escape(chr(10).join(fields))}</pre>")

    messages: list[str] = []
    current = "<b>Your delivery details</b>\n\n"
    for block in blocks:
        if len(current) + len(block) + 2 > 3800:
            messages.append(current.rstrip())
            current = "<b>Delivery details continued</b>\n\n"
        current += f"{block}\n\n"
    if blocks:
        messages.append(current.rstrip())
    return messages


@router.callback_query(PurchaseStates.confirmation, F.data.startswith("shop:confirm:"))
async def execute_purchase(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if not settings.catalog_enabled:
        await state.clear()
        await callback.answer("Products are temporarily unavailable.", show_alert=True)
        return
    _, _, product_id, quantity_raw, months_raw = callback.data.split(":")
    data = await state.get_data()
    quantity = int(quantity_raw)
    slot_months = int(months_raw) or None
    if (
        data.get("product_id") != product_id
        or int(data.get("quantity", 0)) != quantity
        or data.get("slot_months") != slot_months
        or not data.get("idempotency_key")
    ):
        await state.clear()
        await callback.answer("This confirmation expired. Please start again.", show_alert=True)
        return

    if callback.message is not None:
        await render_text_message(
            callback.message,
            "<b>Processing purchase…</b>\n\nPlease wait and do not close the chat.",
            EMPTY_KEYBOARD,
        )

    try:
        completed = await OrderService(session).purchase(
            callback.from_user.id,
            product_id,
            quantity=quantity,
            customer_email=data.get("customer_email"),
            slot_months=slot_months,
            idempotency_key=str(data["idempotency_key"]),
        )
    except InsufficientBalanceError:
        await callback.answer("Insufficient shop balance.", show_alert=True)
        if callback.message is not None:
            await render_text_message(
                callback.message,
                "<b>Insufficient Balance</b>\n\nTop up your shop wallet, then try again.",
                back_to_menu_keyboard(),
            )
        return
    except OutOfStockError:
        await callback.answer("This product just sold out.", show_alert=True)
        return
    except ProviderError as exc:
        logger.warning("Provider purchase failed: status=%s", getattr(exc, "status", None))
        await callback.answer(_provider_message(exc), show_alert=True)
        if callback.message is not None:
            await render_text_message(
                callback.message,
                f"<b>Purchase Not Completed</b>\n\n{html.escape(_provider_message(exc))}",
                back_to_menu_keyboard(),
            )
        return

    await state.clear()
    account = await UserService(session).get_profile(callback.from_user.id)
    summary = _purchase_summary(
        completed.provider, completed.local_order.price, completed.local_order.currency
    )
    summary += f"\nRemaining balance: {html.escape(format_money(account.balance, completed.local_order.currency))}"
    if callback.message is not None:
        await render_text_message(callback.message, summary, back_to_menu_keyboard())
        for delivery_message in _delivery_messages(completed.provider):
            await callback.message.answer(delivery_message)
    await callback.answer("Purchase successful!")
