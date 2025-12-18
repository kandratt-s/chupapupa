import asyncio
from aiogram import Bot, Dispatcher
from services.bot.gateway_bot.config import BOT_TOKEN

from services.bot.gateway_bot.handlers.auth import auth_router
from services.bot.gateway_bot.handlers.student import student_router
from services.bot.gateway_bot.handlers.admin_apps import admin_apps_router
from services.bot.gateway_bot.handlers.common import common_router


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(auth_router)
    dp.include_router(student_router)
    dp.include_router(admin_apps_router)
    dp.include_router(common_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
