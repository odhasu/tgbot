"""Admin statistics dashboard."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import back_to_admin_keyboard
from services.admin_service import AdminService
from utils.formatting import format_price

router = Router(name="admin_stats")


@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    service = AdminService(session)
    stats = await service.get_stats()

    popular = stats.most_popular_product or "—"
    text = (
        "📊 <b>Statistics</b>\n\n"
        f"Total Users: {stats.total_users}\n"
        f"Total Orders: {stats.total_orders}\n"
        f"Revenue: {format_price(stats.revenue)}\n"
        f"Products Sold: {stats.products_sold}\n"
        f"Most Popular Product: {popular}"
    )

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=back_to_admin_keyboard())
    await callback.answer()
