"""Service layer — business logic. Handlers call these, never repositories directly."""

from services.admin_service import AdminService, ShopStats
from services.order_service import OrderService
from services.shop_service import ShopService
from services.user_service import UserService

__all__ = [
    "AdminService",
    "OrderService",
    "ShopService",
    "ShopStats",
    "UserService",
]
