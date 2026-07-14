"""Bot entrypoint: wires config, logging, database, middlewares, and routers together."""

from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from aiohttp import web

from config import settings
from database import init_db, session_factory
from handlers import build_root_router
from middlewares.ban_check import BanCheckMiddleware
from middlewares.db_session import DbSessionMiddleware
from services.seed import apply_price_increase_once, seed_default_catalog
from utils.logger import get_logger, setup_logging

logger = get_logger("shopbot.bot")


async def run_health_server() -> None:
    """Bind $PORT so Render (or similar PaaS) sees a live HTTP service to ping."""
    port = os.environ.get("PORT")
    if not port:
        return
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()
    logger.info("Health server listening on port %s", port)


async def on_error(event: ErrorEvent) -> bool:
    logger.error("Unhandled exception while processing update", exc_info=event.exception)

    update = event.update
    chat_message = update.message or (update.callback_query.message if update.callback_query else None)
    if chat_message is not None:
        try:
            await chat_message.answer("Something went wrong. Please try again in a moment.")
        except Exception:
            logger.exception("Failed to notify user about the error")
    return True


async def main() -> None:
    setup_logging()
    logger.info("Starting up ShopBot")

    os.makedirs("data", exist_ok=True)
    await init_db()
    logger.info("Database ready")

    async with session_factory() as session:
        await seed_default_catalog(session)
        await apply_price_increase_once(session)

    await run_health_server()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()

    dispatcher.update.middleware(DbSessionMiddleware())
    dispatcher.update.middleware(BanCheckMiddleware())
    dispatcher.include_router(build_root_router())
    dispatcher.errors.register(on_error)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Polling started")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
