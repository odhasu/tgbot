"""Admin order management: list, view, change status."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import order_detail_keyboard, orders_list_keyboard
from models.enums import OrderStatus
from models.order import Order
from services.exceptions import OrderNotFoundError
from services.order_service import OrderService
from utils.formatting import format_price

router = Router(name="admin_orders")

STATUS_MAP = {
    "completed": OrderStatus.COMPLETED,
    "pending": OrderStatus.PENDING,
    "cancelled": OrderStatus.CANCELLED,
    "refunded": OrderStatus.REFUNDED,
}


def _order_detail_text(order: Order) -> str:
    date = order.created_at.strftime("%Y-%m-%d %H:%M")
    return (
        f"🧾 <b>Order #{order.id}</b>\n\n"
        f"Product: {order.product_name}\n"
        f"Price: {format_price(order.price)}\n"
        f"Status: {order.status.value}\n"
        f"Date: {date}"
    )


@router.callback_query(F.data == "admin:orders")
async def list_orders(callback: CallbackQuery, session: AsyncSession) -> None:
    service = OrderService(session)
    orders = await service.list_all_orders(limit=20)
    text = "🧾 <b>Orders</b>\n\nMost recent:" if orders else "🧾 <b>Orders</b>\n\nNo orders yet."
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=orders_list_keyboard(orders))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:orders:view:"))
async def view_order(callback: CallbackQuery, session: AsyncSession) -> None:
    order_id = int(callback.data.split(":")[3])
    service = OrderService(session)
    try:
        order = await service.get_order(order_id)
    except OrderNotFoundError:
        await callback.answer("❌ Order not found.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(_order_detail_text(order), reply_markup=order_detail_keyboard(order))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:orders:status:"))
async def change_order_status(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, _, order_id_raw, status_raw = callback.data.split(":")
    service = OrderService(session)
    try:
        order = await service.update_status(
            int(order_id_raw), STATUS_MAP[status_raw], actor_telegram_id=callback.from_user.id
        )
    except OrderNotFoundError:
        await callback.answer("❌ Order not found.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(_order_detail_text(order), reply_markup=order_detail_keyboard(order))
    await callback.answer("Status updated.")
