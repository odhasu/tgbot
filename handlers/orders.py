"""Order history view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import back_to_menu_keyboard
from models.enums import OrderStatus
from services.order_service import OrderService
from utils.formatting import format_price

router = Router(name="orders")

STATUS_ICONS = {
    OrderStatus.PENDING: "⏳",
    OrderStatus.COMPLETED: "✅",
    OrderStatus.CANCELLED: "❌",
    OrderStatus.REFUNDED: "↩️",
}


@router.callback_query(F.data == "menu:orders")
async def show_orders(callback: CallbackQuery, session: AsyncSession) -> None:
    service = OrderService(session)
    orders = await service.list_user_orders(callback.from_user.id)

    if not orders:
        text = "📦 <b>Orders</b>\n\nYou haven't placed any orders yet."
    else:
        lines = ["📦 <b>Orders</b>\n"]
        for order in orders:
            icon = STATUS_ICONS.get(order.status, "•")
            date = order.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(
                f"{icon} #{order.id} — {order.product_name} — {format_price(order.price)} — {date}"
            )
        text = "\n".join(lines)

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
