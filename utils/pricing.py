"""Shared pricing rules."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from config import settings

WARRANTY_PRICE = Decimal("10")
RETAIL_PRICE_MULTIPLIER = settings.retail_price_multiplier


def retail_price(wholesale_amount: Decimal, currency: str) -> Decimal:
    """Apply the configured markup and round to the wallet currency's spendable unit."""
    precision = Decimal("1") if currency.upper() == "VND" else Decimal("0.000001")
    return (wholesale_amount * RETAIL_PRICE_MULTIPLIER).quantize(
        precision, rounding=ROUND_HALF_UP
    )
