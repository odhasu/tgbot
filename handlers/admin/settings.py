"""Admin-editable bot text settings."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import cancel_keyboard, settings_menu_keyboard
from services.settings_service import SettingsService
from states.admin_states import EditSettingsStates
from utils.telegram import render_text_message

router = Router(name="admin_settings")

_LABELS = {"welcome_text": "Welcome Text"}


@router.callback_query(F.data == "admin:settings")
async def show_settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await render_text_message(
            callback.message, "<b>Settings</b>\n\nChoose a setting to edit:", settings_menu_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:settings:edit:"))
async def start_edit_setting(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    key = callback.data.split(":")[3]
    await state.update_data(key=key)
    await state.set_state(EditSettingsStates.value)

    current = await SettingsService(session).get_welcome_text()
    label = _LABELS.get(key, key)
    text = (
        f"Current {label}:\n\n{current}\n\n"
        f"Send the new {label.lower()}. Use <code>{{name}}</code> where the user's name should go."
    )
    if callback.message is not None:
        await render_text_message(callback.message, text, cancel_keyboard())
    await callback.answer()


@router.message(EditSettingsStates.value)
async def apply_setting_edit(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    key = data["key"]
    value = (message.text or "").strip()
    if not value:
        await message.answer("Can't be empty. Send the new text:", reply_markup=cancel_keyboard())
        return

    await state.clear()
    if key == "welcome_text":
        await SettingsService(session).set_welcome_text(value)

    await message.answer("Setting updated.", reply_markup=settings_menu_keyboard())
