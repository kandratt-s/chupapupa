from aiogram import Bot, Dispatcher

from ..config import BOT_TOKEN
from ..handlers.auth import auth_router
from ..handlers.student import student_router
from ..handlers.admin_events import admin_events_router
from ..handlers.admin_users import admin_users_router
from ..handlers.admin_apps import admin_apps_router
from ..handlers.common import common_router


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Порядок важен! auth первым
    dp.include_router(auth_router)
    dp.include_router(admin_events_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_apps_router)
    dp.include_router(student_router)
    dp.include_router(common_router)

    await dp.start_polling(bot)
