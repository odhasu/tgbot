"""Shared enum types used across ORM models."""

from __future__ import annotations

import enum


class DeliveryType(str, enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
