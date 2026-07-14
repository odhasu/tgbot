"""Aggregates all feature routers in the order they should be checked.

Feature-specific routers (shop, balance, orders, ...) must be included
*before* menu_router, since menu_router's placeholder handler matches any
still-unimplemented menu:* callback.
"""

from aiogram import Router

from handlers.admin import build_admin_router
from handlers.balance import router as balance_router
from handlers.deposit import router as deposit_router
from handlers.menu import router as menu_router
from handlers.profile import router as profile_router
from handlers.shop import router as shop_router
from handlers.start import router as start_router
from handlers.support import router as support_router


def build_root_router() -> Router:
    root = Router(name="root")
    root.include_router(start_router)
    root.include_router(shop_router)
    root.include_router(balance_router)
    root.include_router(deposit_router)
    root.include_router(profile_router)
    root.include_router(support_router)
    root.include_router(build_admin_router())
    root.include_router(menu_router)
    return root
