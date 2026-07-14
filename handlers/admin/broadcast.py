"""Admin broadcast: compose, preview, confirm, send to all users."""

from __future__ import annotations

import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import back_to_admin_keyboard, broadcast_confirm_keyboard, cancel_keyboard
from services.admin_service import AdminService
from states.admin_states import BroadcastStates
from utils.logger import get_logger

logger = get_logger("shopbot.handlers.admin.broadcast")

router = Router(name="admin_broadcast")


@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastStates.message)
    if callback.message is not None:
        await callback.message.edit_text(
            "Send the message to broadcast to all users:", reply_markup=cancel_keyboard()
        )
    await callback.answer()


@router.message(BroadcastStates.message)
async def preview_broadcast(message: Message, state: FSMContext) -> None:
    text = message.text or message.caption
    if not text:
        await message.answer("Please send a text message to broadcast:", reply_markup=cancel_keyboard())
        return

    await state.update_data(text=text)
    await state.set_state(BroadcastStates.confirm)
    await message.answer(f"Preview:\n\n{text}\n\nSend this to all users?", reply_markup=broadcast_confirm_keyboard())


@router.callback_query(BroadcastStates.confirm, F.data == "admin:broadcast:send")
async def send_broadcast(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    text = data.get("text", "")

    service = AdminService(session)
    targets = await service.get_broadcast_targets()

    sent = 0
    for telegram_id in targets:
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            logger.warning("Broadcast failed for telegram_id=%s", telegram_id, exc_info=True)
        await asyncio.sleep(0.05)

    service.log_broadcast(callback.from_user.id, sent, text)

    if callback.message is not None:
        await callback.message.edit_text(
            f"Broadcast sent to {sent}/{len(targets)} users.", reply_markup=back_to_admin_keyboard()
        )
    await callback.answer()
