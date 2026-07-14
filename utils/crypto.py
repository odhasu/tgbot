"""Static crypto deposit addresses and QR code generation."""

from __future__ import annotations

import io

import qrcode
from aiogram.types import BufferedInputFile

MIN_DEPOSIT_USD = 10

CRYPTO_LABELS: dict[str, str] = {
    "BTC": "BTC",
    "ETH": "ETH",
    "USDT_ERC20": "USDT (ERC20)",
    "SOL": "SOL",
    "LTC": "LTC",
}

CRYPTO_ADDRESSES: dict[str, str] = {
    "BTC": "bc1qcg8jkhgvy73rt0x2lqy9czsuc47xykd6najks0",
    "ETH": "0xdDcD2A98B6d95f0a1792deC94A4d6519E46DfF23",
    "USDT_ERC20": "0xdDcD2A98B6d95f0a1792deC94A4d6519E46DfF23",
    "SOL": "3X2cnddUUem7dhTc4cv3kyrgd1YcJD153yKhBzYMUGsi",
    "LTC": "LSUyVSxmWsKzJyRKPTJcSXUMCbkr2ZCaHR",
}

def make_qr_photo(coin: str, address: str) -> BufferedInputFile:
    img = qrcode.make(address)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return BufferedInputFile(buffer.read(), filename=f"{coin}_qr.png")
