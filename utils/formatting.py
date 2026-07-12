"""Shared text formatting helpers."""

from __future__ import annotations

from decimal import Decimal


def format_price(amount: Decimal) -> str:
    return f"${amount:.2f}"
