import asyncio
import logging
from bot.config import dp, bot, log
from bot.handlers import router
from bot.scheduler import start_scheduler


async def main():
    dp.include_router(router)
    start_scheduler()
    log.info("🚀 Бот запущен.")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())