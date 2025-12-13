from aiogram import Router, types
from services.bot.gateway_bot.fsm.fsm import fsm
from services.bot.gateway_bot.keyboards import (
    build_admin_menu,
    build_user_menu,
    login_kb,
)

common_router = Router()


@common_router.callback_query(lambda c: c.data == "btn_back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    session = f.get()
    role = session.get("role")
    token = session.get("token")

    if not token:
        await f.show_menu(callback.bot, chat_id, "👋 Войдите в систему:", login_kb())
        await callback.answer()
        return

    if role == "admin":
        await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    else:
        await f.show_menu(callback.bot, chat_id, "🎓 Меню студента", build_user_menu())

    await callback.answer()
