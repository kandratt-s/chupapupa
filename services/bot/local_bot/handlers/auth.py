from aiogram import Router, types
from aiogram.filters import Command

from services.bot.local_bot.storage import tokens
from services.bot.local_bot.keyboards import (
    build_admin_menu,
    build_user_menu,
    login_kb,
)
from services.bot.local_bot.fsm import fsm

auth_router = Router()


@auth_router.message(Command("start"))
async def start(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    # Удаляем prompts
    await f.clear_prompts(message.bot, chat_id)

    # Удаляем старое меню
    st = f.get()
    old_menu_id = st.get("menu_id")
    if old_menu_id:
        try:
            await message.bot.delete_message(chat_id, old_menu_id)
        except:
            pass

    # Удаляем inline-кнопки у последнего сообщения
    try:
        await message.bot.edit_message_reply_markup(chat_id, chat_id, reply_markup=None)
    except:
        pass

    # Полный сброс FSM
    f.clear()

    # Определяем роль
    role = tokens.get(uid, {}).get("role")

    # ЕДИНОЕ МЕНЮ ДЛЯ ВСЕХ
    if role == "admin":
        await f.show_menu(
            message.bot,
            chat_id,
            "👑 Админ‑панель",
            build_admin_menu(),
        )
        return

    if role == "student":
        await f.show_menu(
            message.bot,
            chat_id,
            "🎓 Меню студента",
            build_user_menu(),
        )
        return

    await f.show_menu(
        message.bot,
        chat_id,
        "👋 Привет! Войдите в систему:",
        login_kb(),
    )
