import os
import sys

sys.path.append(os.getcwd())

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import core as db
from handlers import base, user_history, user_statistics
from utils.bot_logging import get_logger, setup_logging

setup_logging(name="TimeTracker", log_file="bot.log", level=logging.INFO)

main_logger = get_logger("main")


async def main() -> None:
    try:
        await db.init_db()
        main_logger.info("Базы инициализированы")

        bot = Bot(
            token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()

        # dp.include_router(basic_commands.router)
        dp.include_router(base.router)
        dp.include_router(user_history.router)
        dp.include_router(user_statistics.router)

        # await bot.delete_webhook(drop_pending_updates=True)
        main_logger.info("Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        main_logger.critical(f"Критическая ошибка при запуске: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Bot was interrupted.")
        print("Bot was interrupted.")
