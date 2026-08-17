"""Admin panel router — all callbacks/messages here require IsAdmin."""

from aiogram import Router

from filters.admin_filter import IsAdmin
from handlers.admin.broadcast import router as broadcast_router
from handlers.admin.menu import router as menu_router
from handlers.admin.orders import router as orders_router
from handlers.admin.provider import router as provider_router
from handlers.admin.settings import router as settings_router
from handlers.admin.stats import router as stats_router
from handlers.admin.users import router as users_router


def build_admin_router() -> Router:
    root = Router(name="admin")
    root.message.filter(IsAdmin())
    root.callback_query.filter(IsAdmin())

    root.include_router(menu_router)
    root.include_router(users_router)
    root.include_router(orders_router)
    root.include_router(provider_router)
    root.include_router(broadcast_router)
    root.include_router(stats_router)
    root.include_router(settings_router)
    return root
