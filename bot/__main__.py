"""Entry point: python -m bot"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BusinessProvider, Settings
from bot.handlers import admin, client
from bot.storage import BookingRepository


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    repo = BookingRepository(settings.db_path)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(
        settings=settings,
        business=BusinessProvider(settings.business_config),
        repo=repo,
    )
    if settings.admin_id is not None:
        dp.include_router(admin.build_router(settings.admin_id))  # before client's fallback
    else:
        logging.warning("ADMIN_ID is not set: bookings and questions won't be forwarded")
    dp.include_router(client.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        repo.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
