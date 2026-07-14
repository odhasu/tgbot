"""Static section banner images shown as photo headers on menu screens."""

from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message

BANNER_DIR = Path(__file__).resolve().parent.parent / "assets" / "banners"

BANNER_FILES: dict[str, Path] = {
    "vex": BANNER_DIR / "vex.webp",
    "shop": BANNER_DIR / "shop.webp",
    "balance": BANNER_DIR / "balance.webp",
    "topup": BANNER_DIR / "topup.webp",
    "profile": BANNER_DIR / "profile.webp",
}

_file_id_cache: dict[str, str] = {}


async def render_banner_message(
    message: Message,
    banner_key: str,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """Replace `message` with a photo message: banner image + caption + keyboard."""
    photo = _file_id_cache.get(banner_key) or FSInputFile(BANNER_FILES[banner_key])
    await message.delete()
    sent = await message.answer_photo(photo, caption=text, reply_markup=reply_markup)
    if banner_key not in _file_id_cache and sent.photo:
        _file_id_cache[banner_key] = sent.photo[-1].file_id
