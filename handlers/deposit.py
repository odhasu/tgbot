"""Crypto deposit flow: pick a coin, show address + QR code."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.deposit import deposit_address_keyboard, deposit_coins_keyboard
from utils.banners import render_banner_message
from utils.crypto import CRYPTO_ADDRESSES, CRYPTO_LABELS, MIN_DEPOSIT_USD, make_qr_photo

router = Router(name="deposit")

_qr_file_id_cache: dict[str, str] = {}


@router.callback_query(F.data == "menu:deposit")
async def show_coin_list(callback: CallbackQuery) -> None:
    text = (
        "<b>Deposit Funds</b>\n\n"
        f"Minimum deposit: ${MIN_DEPOSIT_USD}\n\n"
        "Choose a coin:"
    )
    if callback.message is not None:
        await render_banner_message(callback.message, "topup", text, deposit_coins_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("deposit:coin:"))
async def show_address(callback: CallbackQuery) -> None:
    coin = callback.data.split(":")[2]
    address = CRYPTO_ADDRESSES.get(coin)
    if address is None:
        await callback.answer("Unknown coin.", show_alert=True)
        return

    label = CRYPTO_LABELS[coin]
    text = (
        f"<b>{label} Deposit</b>\n\n"
        f"Minimum deposit: ${MIN_DEPOSIT_USD}\n\n"
        f"Send {label} to the address below:\n\n"
        f"<code>{address}</code>\n\n"
        "Your payment will be verified and credited automatically.\n"
        "No admin contact is required."
    )

    if callback.message is not None:
        await callback.message.delete()
        photo = _qr_file_id_cache.get(coin) or make_qr_photo(coin, address)
        sent = await callback.message.answer_photo(
            photo, caption=text, reply_markup=deposit_address_keyboard()
        )
        if coin not in _qr_file_id_cache and sent.photo:
            _qr_file_id_cache[coin] = sent.photo[-1].file_id
    await callback.answer()
