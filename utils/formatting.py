"""Shared text formatting helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


def format_price(amount: Decimal) -> str:
    return format_money(amount, "USD")


def format_money(amount: Decimal, currency: str) -> str:
    currency = currency.upper()
    if currency == "USD":
        rendered = f"{amount:.6f}".rstrip("0").rstrip(".")
        if "." not in rendered:
            rendered += ".00"
        elif len(rendered.rsplit(".", 1)[1]) == 1:
            rendered += "0"
        return f"${rendered}"
    if currency == "VND":
        return f"{amount:,.0f} ₫"
    return f"{amount.normalize()} {currency}"


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Render a (possibly naive, assumed-UTC) datetime in Amsterdam local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(AMSTERDAM_TZ).strftime(fmt)
