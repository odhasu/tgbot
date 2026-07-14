"""Admin category management: list, view/edit, add (multi-step), toggle, delete."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import (
    cancel_keyboard,
    categories_list_keyboard,
    category_delete_confirm_keyboard,
    category_detail_keyboard,
    skip_description_keyboard,
    skip_sort_order_keyboard,
)
from models.category import Category
from services.exceptions import CategoryAlreadyExistsError, CategoryNotFoundError
from services.shop_service import ShopService
from states.admin_states import AddCategoryStates, EditCategoryStates
from utils.telegram import render_text_message

router = Router(name="admin_categories")


def _category_detail_text(category: Category) -> str:
    status = "Active" if category.is_active else "Inactive"
    description = category.description or "(none)"
    return (
        f"<b>{category.name}</b>\n\n"
        f"Description: {description}\n"
        f"Sort Order: {category.sort_order}\n"
        f"Status: {status}"
    )


@router.callback_query(F.data == "admin:categories")
async def list_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = ShopService(session)
    categories = await service.list_categories(active_only=False)
    text = (
        "<b>Categories</b>\n\nSelect a category, or add a new one:"
        if categories
        else "<b>Categories</b>\n\nNo categories yet."
    )
    if callback.message is not None:
        await render_text_message(callback.message, text, categories_list_keyboard(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:categories:view:"))
async def view_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        category = await service.get_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("Category not found.", show_alert=True)
        return
    if callback.message is not None:
        await render_text_message(
            callback.message, _category_detail_text(category), category_detail_keyboard(category)
        )
    await callback.answer()


@router.callback_query(F.data == "admin:categories:add")
async def start_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddCategoryStates.name)
    if callback.message is not None:
        await callback.message.edit_text("Send the new category name:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddCategoryStates.name)
async def set_category_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Name can't be empty. Send the category name:", reply_markup=cancel_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(AddCategoryStates.description)
    await message.answer("Send a description, or skip:", reply_markup=skip_description_keyboard())


async def _prompt_sort_order(message_or_callback, state: FSMContext) -> None:
    await state.set_state(AddCategoryStates.sort_order)
    await message_or_callback.answer(
        "Send a sort order number (lower shows first), or skip to use 0:",
        reply_markup=skip_sort_order_keyboard(),
    )


@router.message(AddCategoryStates.description)
async def set_category_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    await state.update_data(description=description or None)
    await _prompt_sort_order(message, state)


@router.callback_query(AddCategoryStates.description, F.data == "admin:categories:add:skip_description")
async def skip_category_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description=None)
    await state.set_state(AddCategoryStates.sort_order)
    if callback.message is not None:
        await render_text_message(
            callback.message,
            "Send a sort order number (lower shows first), or skip to use 0:",
            skip_sort_order_keyboard(),
        )
    await callback.answer()


async def _create_category_from_state(state: FSMContext, session: AsyncSession, sort_order: int) -> Category:
    data = await state.get_data()
    await state.clear()
    service = ShopService(session)
    return await service.create_category(
        name=data["name"], description=data.get("description"), sort_order=sort_order
    )


@router.message(AddCategoryStates.sort_order)
async def set_category_sort_order(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("Invalid number. Send a whole number, or skip:", reply_markup=skip_sort_order_keyboard())
        return

    try:
        category = await _create_category_from_state(state, session, int(raw))
    except CategoryAlreadyExistsError:
        await message.answer("A category with that name already exists.")
        return

    await message.answer(
        f"Category created!\n\n{_category_detail_text(category)}",
        reply_markup=category_detail_keyboard(category),
    )


@router.callback_query(AddCategoryStates.sort_order, F.data == "admin:categories:add:skip_sort_order")
async def skip_category_sort_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    try:
        category = await _create_category_from_state(state, session, 0)
    except CategoryAlreadyExistsError:
        await callback.answer("A category with that name already exists.", show_alert=True)
        return

    if callback.message is not None:
        await render_text_message(
            callback.message,
            f"Category created!\n\n{_category_detail_text(category)}",
            category_detail_keyboard(category),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:categories:edit:"))
async def start_edit_category(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, category_id_raw, field = callback.data.split(":")
    await state.update_data(category_id=int(category_id_raw), field=field)
    await state.set_state(EditCategoryStates.value)
    prompts = {
        "name": "Send the new category name:",
        "description": "Send the new description:",
        "sort_order": "Send the new sort order number:",
    }
    if callback.message is not None:
        await render_text_message(callback.message, prompts[field], cancel_keyboard())
    await callback.answer()


@router.message(EditCategoryStates.value)
async def apply_category_edit(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = data["field"]
    category_id = data["category_id"]
    raw = (message.text or "").strip()

    value: object
    if field == "sort_order":
        if not raw.lstrip("-").isdigit():
            await message.answer("Invalid number. Send a whole number:", reply_markup=cancel_keyboard())
            return
        value = int(raw)
    elif field == "name":
        if not raw:
            await message.answer("Name can't be empty:", reply_markup=cancel_keyboard())
            return
        value = raw
    else:
        value = raw or None

    await state.clear()
    service = ShopService(session)
    try:
        category = await service.update_category(category_id, **{field: value})
    except CategoryNotFoundError:
        await message.answer("Category no longer exists.")
        return
    except CategoryAlreadyExistsError:
        await message.answer("A category with that name already exists.")
        return

    await message.answer(
        f"Updated!\n\n{_category_detail_text(category)}", reply_markup=category_detail_keyboard(category)
    )


@router.callback_query(F.data.startswith("admin:categories:toggle:"))
async def toggle_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        category = await service.get_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("Category not found.", show_alert=True)
        return
    category = await service.update_category(category_id, is_active=not category.is_active)
    if callback.message is not None:
        await render_text_message(
            callback.message, _category_detail_text(category), category_detail_keyboard(category)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:categories:delete:"))
async def confirm_delete_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        category = await service.get_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("Category not found.", show_alert=True)
        return
    if callback.message is not None:
        await render_text_message(
            callback.message,
            f"Delete <b>{category.name}</b>? Its products will be removed too.",
            category_delete_confirm_keyboard(category_id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:categories:delete_confirm:"))
async def delete_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        await service.delete_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("Category not found.", show_alert=True)
        return
    categories = await service.list_categories(active_only=False)
    if callback.message is not None:
        await render_text_message(
            callback.message, "Category deleted.\n\n<b>Categories</b>", categories_list_keyboard(categories)
        )
    await callback.answer()
