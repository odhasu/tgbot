"""Domain exceptions raised by the service layer. Handlers catch these to show friendly errors."""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for all expected business-rule failures."""


class InsufficientBalanceError(ServiceError):
    pass


class OutOfStockError(ServiceError):
    pass


class ProductNotFoundError(ServiceError):
    pass


class CategoryNotFoundError(ServiceError):
    pass


class CategoryAlreadyExistsError(ServiceError):
    pass


class UserNotFoundError(ServiceError):
    pass


class OrderNotFoundError(ServiceError):
    pass


class NotAdminError(ServiceError):
    pass
