"""Admin category management: list, add, delete."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import cancel_keyboard, categories_list_keyboard, category_delete_confirm_keyboard
from services.exceptions import CategoryAlreadyExistsError, CategoryNotFoundError
from services.shop_service import ShopService
from states.admin_states import AddCategoryStates

router = Router(name="admin_categories")


@router.callback_query(F.data == "admin:categories")
async def list_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = ShopService(session)
    categories = await service.list_categories(active_only=False)
    text = (
        "🗂 <b>Categories</b>\n\nTap a category to delete it, or add a new one:"
        if categories
        else "🗂 <b>Categories</b>\n\nNo categories yet."
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=categories_list_keyboard(categories))
    await callback.answer()


@router.callback_query(F.data == "admin:categories:add")
async def start_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddCategoryStates.name)
    if callback.message is not None:
        await callback.message.edit_text("Send the new category name:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddCategoryStates.name)
async def set_category_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Name can't be empty. Send the category name:", reply_markup=cancel_keyboard())
        return

    await state.clear()
    service = ShopService(session)
    try:
        category = await service.create_category(name)
    except CategoryAlreadyExistsError:
        await message.answer(f"❌ Category {name!r} already exists.")
        return

    categories = await service.list_categories(active_only=False)
    await message.answer(
        f"✅ Category {category.name!r} created.\n\n🗂 <b>Categories</b>",
        reply_markup=categories_list_keyboard(categories),
    )


@router.callback_query(F.data.startswith("admin:categories:delete:"))
async def confirm_delete_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        category = await service.get_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("❌ Category not found.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(
            f"Delete <b>{category.name}</b>? Its products will be removed too.",
            reply_markup=category_delete_confirm_keyboard(category_id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:categories:delete_confirm:"))
async def delete_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        await service.delete_category(category_id)
    except CategoryNotFoundError:
        await callback.answer("❌ Category not found.", show_alert=True)
        return
    categories = await service.list_categories(active_only=False)
    if callback.message is not None:
        await callback.message.edit_text(
            "✅ Category deleted.\n\n🗂 <b>Categories</b>", reply_markup=categories_list_keyboard(categories)
        )
    await callback.answer()
