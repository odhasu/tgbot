"""Shared text formatting helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


def format_price(amount: Decimal) -> str:
    return f"${amount:.2f}"


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Render a (possibly naive, assumed-UTC) datetime in Amsterdam local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(AMSTERDAM_TZ).strftime(fmt)
