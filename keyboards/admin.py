"""Inline keyboards for the admin panel."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.category import Category
from models.order import Order
from models.product import Product
from models.user import User
from utils.formatting import format_price


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Users", callback_data="admin:users")
    builder.button(text="Orders", callback_data="admin:orders")
    builder.button(text="Supplier API", callback_data="admin:provider")
    builder.button(text="Broadcast", callback_data="admin:broadcast")
    builder.button(text="Statistics", callback_data="admin:stats")
    builder.button(text="Settings", callback_data="admin:settings")
    builder.button(text="Back to Menu", callback_data="menu:home")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Cancel", callback_data="admin:cancel")
    return builder.as_markup()


def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Back to Admin", callback_data="admin:menu")
    return builder.as_markup()


# --- Products ---------------------------------------------------------


def products_list_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        label = product.name if product.is_active else f"{product.name} (inactive)"
        builder.button(text=label, callback_data=f"admin:products:view:{product.id}")
    builder.button(text="Add Product", callback_data="admin:products:add")
    builder.button(text="Back to Admin", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Name", callback_data=f"admin:products:edit:{product.id}:name")
    builder.button(text="Description", callback_data=f"admin:products:edit:{product.id}:description")
    builder.button(text="Price", callback_data=f"admin:products:edit:{product.id}:price")
    builder.button(text="Stock", callback_data=f"admin:products:edit:{product.id}:stock")
    builder.button(text="Photo", callback_data=f"admin:products:edit:{product.id}:photo")
    toggle_label = "Deactivate" if product.is_active else "Activate"
    builder.button(text=toggle_label, callback_data=f"admin:products:toggle:{product.id}")
    builder.button(text="Delete", callback_data=f"admin:products:delete:{product.id}")
    builder.button(text="Back", callback_data="admin:products")
    builder.adjust(2, 2, 1, 1, 1, 1)
    return builder.as_markup()


def product_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Confirm Delete", callback_data=f"admin:products:delete_confirm:{product_id}")
    builder.button(text="Cancel", callback_data=f"admin:products:view:{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def category_pick_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=f"admin:products:add:cat:{category.id}")
    builder.button(text="Cancel", callback_data="admin:products")
    builder.adjust(1)
    return builder.as_markup()


def delivery_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Manual", callback_data="admin:products:add:delivery:manual")
    builder.button(text="Automatic", callback_data="admin:products:add:delivery:automatic")
    builder.adjust(2)
    return builder.as_markup()


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Skip", callback_data="admin:products:add:photo:skip")
    builder.button(text="Cancel", callback_data="admin:cancel")
    builder.adjust(2)
    return builder.as_markup()


# --- Categories ---------------------------------------------------------


def categories_list_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        label = category.name if category.is_active else f"{category.name} (inactive)"
        builder.button(text=label, callback_data=f"admin:categories:view:{category.id}")
    builder.button(text="Add Category", callback_data="admin:categories:add")
    builder.button(text="Back to Admin", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def category_detail_keyboard(category: Category) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Name", callback_data=f"admin:categories:edit:{category.id}:name")
    builder.button(text="Description", callback_data=f"admin:categories:edit:{category.id}:description")
    builder.button(text="Sort Order", callback_data=f"admin:categories:edit:{category.id}:sort_order")
    toggle_label = "Deactivate" if category.is_active else "Activate"
    builder.button(text=toggle_label, callback_data=f"admin:categories:toggle:{category.id}")
    builder.button(text="Delete", callback_data=f"admin:categories:delete:{category.id}")
    builder.button(text="Back", callback_data="admin:categories")
    builder.adjust(2, 1, 1, 1, 1)
    return builder.as_markup()


def category_delete_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Confirm Delete", callback_data=f"admin:categories:delete_confirm:{category_id}")
    builder.button(text="Cancel", callback_data=f"admin:categories:view:{category_id}")
    builder.adjust(1)
    return builder.as_markup()


def skip_description_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Skip", callback_data="admin:categories:add:skip_description")
    builder.button(text="Cancel", callback_data="admin:cancel")
    builder.adjust(2)
    return builder.as_markup()


def skip_sort_order_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Skip (use 0)", callback_data="admin:categories:add:skip_sort_order")
    builder.button(text="Cancel", callback_data="admin:cancel")
    builder.adjust(2)
    return builder.as_markup()


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Welcome Text", callback_data="admin:settings:edit:welcome_text")
    builder.button(text="Back to Admin", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


# --- Users ---------------------------------------------------------


def users_list_keyboard(users: list[User]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user in users:
        label = f"{user.display_name} ({format_price(user.balance)})"
        if user.is_banned:
            label += " [banned]"
        builder.button(text=label, callback_data=f"admin:users:view:{user.id}")
    builder.button(text="Search", callback_data="admin:users:search")
    builder.button(text="Back to Admin", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def user_detail_keyboard(user: User) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Add Balance", callback_data=f"admin:users:balance:add:{user.id}")
    builder.button(text="Remove Balance", callback_data=f"admin:users:balance:remove:{user.id}")
    ban_label = "Unban" if user.is_banned else "Ban"
    builder.button(text=ban_label, callback_data=f"admin:users:ban_toggle:{user.id}")
    builder.button(text="Back", callback_data="admin:users")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


# --- Orders ---------------------------------------------------------


def orders_list_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(text=f"#{order.id} — {order.product_name}", callback_data=f"admin:orders:view:{order.id}")
    builder.button(text="Back to Admin", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def order_detail_keyboard(order: Order) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Completed", callback_data=f"admin:orders:status:{order.id}:completed")
    builder.button(text="Pending", callback_data=f"admin:orders:status:{order.id}:pending")
    builder.button(text="Cancelled", callback_data=f"admin:orders:status:{order.id}:cancelled")
    builder.button(text="Refunded", callback_data=f"admin:orders:status:{order.id}:refunded")
    builder.button(text="Back", callback_data="admin:orders")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


# --- Broadcast ---------------------------------------------------------


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Send", callback_data="admin:broadcast:send")
    builder.button(text="Cancel", callback_data="admin:cancel")
    builder.adjust(2)
    return builder.as_markup()
