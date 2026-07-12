"""Admin user management: list, search, view, balance adjustment."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import cancel_keyboard, user_detail_keyboard, users_list_keyboard
from models.user import User
from services.exceptions import UserNotFoundError
from services.user_service import UserService
from states.admin_states import BalanceStates, SearchUserStates
from utils.formatting import format_price

router = Router(name="admin_users")


def _user_detail_text(user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    return (
        f"👤 <b>{user.display_name}</b>\n\n"
        f"Username: {username}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Balance: {format_price(user.balance)}\n"
        f"Total Orders: {user.total_orders}\n"
        f"Total Spent: {format_price(user.total_spent)}\n"
        f"Admin: {'Yes' if user.is_admin else 'No'}"
    )


@router.callback_query(F.data == "admin:users")
async def list_users(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = UserService(session)
    users = await service.list_users(limit=20)
    text = "👥 <b>Users</b>\n\nMost recently joined:" if users else "👥 <b>Users</b>\n\nNo users yet."
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=users_list_keyboard(users))
    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def start_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchUserStates.query)
    if callback.message is not None:
        await callback.message.edit_text(
            "Send a username, name, or Telegram ID to search:", reply_markup=cancel_keyboard()
        )
    await callback.answer()


@router.message(SearchUserStates.query)
async def run_search(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    await state.clear()
    service = UserService(session)
    results = await service.search_users(query)
    text = f"🔍 Results for {query!r}:" if results else f"No users found for {query!r}."
    await message.answer(text, reply_markup=users_list_keyboard(results))


@router.callback_query(F.data.startswith("admin:users:view:"))
async def view_user(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = int(callback.data.split(":")[3])
    service = UserService(session)
    user = await service.get_by_id(user_id)
    if user is None:
        await callback.answer("❌ User not found.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(_user_detail_text(user), reply_markup=user_detail_keyboard(user))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:balance:"))
async def start_balance_adjust(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, direction, user_id_raw = callback.data.split(":")
    await state.update_data(user_id=int(user_id_raw), direction=direction)
    await state.set_state(BalanceStates.amount)
    verb = "add to" if direction == "add" else "remove from"
    if callback.message is not None:
        await callback.message.edit_text(
            f"Send the amount to {verb} this user's balance (e.g. 10.00):", reply_markup=cancel_keyboard()
        )
    await callback.answer()


@router.message(BalanceStates.amount)
async def apply_balance_adjust(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    try:
        amount = Decimal(raw)
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("Invalid amount. Send a positive number (e.g. 10.00):", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    user_id = data["user_id"]
    direction = data["direction"]

    service = UserService(session)
    user = await service.get_by_id(user_id)
    if user is None:
        await state.clear()
        await message.answer("❌ User no longer exists.")
        return

    if direction == "remove" and amount > user.balance:
        await message.answer(
            f"❌ Amount exceeds current balance ({format_price(user.balance)}). Send a smaller amount:",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.clear()
    delta = amount if direction == "add" else -amount
    user = await service.adjust_balance(user_id, delta, actor_telegram_id=message.from_user.id)
    await message.answer(
        f"✅ Balance updated.\n\n{_user_detail_text(user)}", reply_markup=user_detail_keyboard(user)
    )
