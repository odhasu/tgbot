"""Admin product CRUD: list, view, add (multi-step), edit, toggle, delete."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin import (
    cancel_keyboard,
    category_pick_keyboard,
    delivery_type_keyboard,
    product_delete_confirm_keyboard,
    product_detail_keyboard,
    products_list_keyboard,
    skip_photo_keyboard,
)
from models.enums import DeliveryType
from models.product import Product
from services.exceptions import ProductNotFoundError
from services.shop_service import ShopService
from states.admin_states import AddProductStates, EditProductStates
from utils.telegram import render_product_message, render_text_message

router = Router(name="admin_products")


def _product_detail_text(product: Product) -> str:
    status = "🟢 Active" if product.is_active else "🔴 Inactive"
    return (
        f"📦 <b>{product.name}</b>\n\n"
        f"{product.description}\n\n"
        f"Price: ${product.price:.2f}\n"
        f"Stock: {product.stock}\n"
        f"Delivery: {product.delivery_type.value}\n"
        f"Status: {status}"
    )


@router.callback_query(F.data == "admin:products")
async def list_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = ShopService(session)
    products = await service.list_all_products()
    text = (
        "📦 <b>Products</b>\n\nSelect a product, or add a new one:"
        if products
        else "📦 <b>Products</b>\n\nNo products yet."
    )
    if callback.message is not None:
        await render_text_message(callback.message, text, products_list_keyboard(products))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:products:view:"))
async def view_product(callback: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        product = await service.get_product(product_id)
    except ProductNotFoundError:
        await callback.answer("❌ Product not found.", show_alert=True)
        return
    if callback.message is not None:
        await render_product_message(
            callback.message, _product_detail_text(product), product_detail_keyboard(product), product.photo_file_id
        )
    await callback.answer()


@router.callback_query(F.data == "admin:products:add")
async def start_add_product(callback: CallbackQuery, session: AsyncSession) -> None:
    service = ShopService(session)
    categories = await service.list_categories(active_only=False)
    if not categories:
        await callback.answer("❌ Create a category first.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(
            "📦 <b>Add Product</b>\n\nChoose a category:", reply_markup=category_pick_keyboard(categories)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:products:add:cat:"))
async def pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[4])
    await state.update_data(category_id=category_id)
    await state.set_state(AddProductStates.name)
    if callback.message is not None:
        await callback.message.edit_text("Send the product name:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddProductStates.name)
async def set_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Name can't be empty. Send the product name:", reply_markup=cancel_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(AddProductStates.description)
    await message.answer("Send the product description:", reply_markup=cancel_keyboard())


@router.message(AddProductStates.description)
async def set_product_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    await state.update_data(description=description)
    await state.set_state(AddProductStates.price)
    await message.answer("Send the price (e.g. 9.99):", reply_markup=cancel_keyboard())


@router.message(AddProductStates.price)
async def set_product_price(message: Message, state: FSMContext) -> None:
    try:
        price = Decimal((message.text or "").strip())
        if price <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("Invalid price. Send a positive number (e.g. 9.99):", reply_markup=cancel_keyboard())
        return
    await state.update_data(price=str(price))
    await state.set_state(AddProductStates.stock)
    await message.answer("Send the stock quantity:", reply_markup=cancel_keyboard())


@router.message(AddProductStates.stock)
async def set_product_stock(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Invalid stock. Send a whole number (e.g. 10):", reply_markup=cancel_keyboard())
        return
    await state.update_data(stock=int(text))
    await state.set_state(AddProductStates.delivery_type)
    await message.answer("Choose delivery type:", reply_markup=delivery_type_keyboard())


@router.callback_query(AddProductStates.delivery_type, F.data.startswith("admin:products:add:delivery:"))
async def pick_delivery_type(callback: CallbackQuery, state: FSMContext) -> None:
    delivery_raw = callback.data.split(":")[4]
    delivery_type = DeliveryType.AUTOMATIC if delivery_raw == "automatic" else DeliveryType.MANUAL
    await state.update_data(delivery_type=delivery_type.value)
    await state.set_state(AddProductStates.photo)
    if callback.message is not None:
        await callback.message.edit_text(
            "Send a product photo, or skip:", reply_markup=skip_photo_keyboard()
        )
    await callback.answer()


async def _create_product_from_state(
    state: FSMContext, session: AsyncSession, photo_file_id: str | None
) -> Product:
    data = await state.get_data()
    await state.clear()
    service = ShopService(session)
    return await service.create_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        price=Decimal(data["price"]),
        stock=data["stock"],
        delivery_type=DeliveryType(data["delivery_type"]),
        photo_file_id=photo_file_id,
    )


@router.message(AddProductStates.photo, F.photo)
async def set_product_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    photo_file_id = message.photo[-1].file_id
    product = await _create_product_from_state(state, session, photo_file_id)
    await message.answer(
        f"✅ Product created!\n\n{_product_detail_text(product)}",
        reply_markup=product_detail_keyboard(product),
    )


@router.callback_query(AddProductStates.photo, F.data == "admin:products:add:photo:skip")
async def skip_product_photo(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    product = await _create_product_from_state(state, session, None)
    if callback.message is not None:
        await callback.message.edit_text(
            f"✅ Product created!\n\n{_product_detail_text(product)}",
            reply_markup=product_detail_keyboard(product),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:products:edit:"))
async def start_edit_product(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, product_id_raw, field = callback.data.split(":")
    await state.update_data(product_id=int(product_id_raw), field=field)
    await state.set_state(EditProductStates.value)
    prompts = {
        "name": "Send the new product name:",
        "description": "Send the new product description:",
        "price": "Send the new price (e.g. 9.99):",
        "stock": "Send the new stock quantity:",
        "photo": "Send the new product photo:",
    }
    if callback.message is not None:
        await render_text_message(callback.message, prompts[field], cancel_keyboard())
    await callback.answer()


@router.message(EditProductStates.value, F.photo)
async def apply_product_photo_edit(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    if data.get("field") != "photo":
        return
    product_id = data["product_id"]
    photo_file_id = message.photo[-1].file_id

    await state.clear()
    service = ShopService(session)
    try:
        product = await service.update_product(product_id, photo_file_id=photo_file_id)
    except ProductNotFoundError:
        await message.answer("❌ Product no longer exists.")
        return

    await message.answer_photo(
        photo_file_id,
        caption=f"✅ Updated!\n\n{_product_detail_text(product)}",
        reply_markup=product_detail_keyboard(product),
    )


@router.message(EditProductStates.value)
async def apply_product_edit(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = data["field"]
    product_id = data["product_id"]
    if field == "photo":
        await message.answer("Send a photo, or ❌ Cancel:", reply_markup=cancel_keyboard())
        return
    raw = (message.text or "").strip()

    value: object
    if field == "price":
        try:
            value = Decimal(raw)
            if value <= 0:
                raise InvalidOperation
        except InvalidOperation:
            await message.answer("Invalid price. Send a positive number:", reply_markup=cancel_keyboard())
            return
    elif field == "stock":
        if not raw.isdigit():
            await message.answer("Invalid stock. Send a whole number:", reply_markup=cancel_keyboard())
            return
        value = int(raw)
    elif field == "name":
        if not raw:
            await message.answer("Name can't be empty:", reply_markup=cancel_keyboard())
            return
        value = raw
    else:
        value = raw

    await state.clear()
    service = ShopService(session)
    try:
        product = await service.update_product(product_id, **{field: value})
    except ProductNotFoundError:
        await message.answer("❌ Product no longer exists.")
        return

    await message.answer(
        f"✅ Updated!\n\n{_product_detail_text(product)}", reply_markup=product_detail_keyboard(product)
    )


@router.callback_query(F.data.startswith("admin:products:toggle:"))
async def toggle_product(callback: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        product = await service.get_product(product_id)
    except ProductNotFoundError:
        await callback.answer("❌ Product not found.", show_alert=True)
        return
    product = await service.update_product(product_id, is_active=not product.is_active)
    if callback.message is not None:
        await render_product_message(
            callback.message, _product_detail_text(product), product_detail_keyboard(product), product.photo_file_id
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:products:delete:"))
async def confirm_delete_product(callback: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        product = await service.get_product(product_id)
    except ProductNotFoundError:
        await callback.answer("❌ Product not found.", show_alert=True)
        return
    if callback.message is not None:
        await render_text_message(
            callback.message,
            f"Delete <b>{product.name}</b>? This cannot be undone.",
            product_delete_confirm_keyboard(product_id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:products:delete_confirm:"))
async def delete_product(callback: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(callback.data.split(":")[3])
    service = ShopService(session)
    try:
        await service.delete_product(product_id)
    except ProductNotFoundError:
        await callback.answer("❌ Product not found.", show_alert=True)
        return
    products = await service.list_all_products()
    if callback.message is not None:
        await render_text_message(
            callback.message, "✅ Product deleted.\n\n📦 <b>Products</b>", products_list_keyboard(products)
        )
    await callback.answer()
