"""Admin dashboard entry point and FSM-flow cancel button."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.admin import admin_menu_keyboard
from utils.telegram import render_text_message

router = Router(name="admin_menu")


@router.callback_query(F.data.in_({"menu:admin", "admin:menu"}))
async def show_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = "<b>Admin Panel</b>\n\nChoose a section:"
    if callback.message is not None:
        await render_text_message(callback.message, text, admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_admin_menu(callback, state)
