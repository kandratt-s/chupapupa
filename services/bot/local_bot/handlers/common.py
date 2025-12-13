from aiogram import Router, types
from aiogram.filters import Command

from services.bot.local_bot.storage import tokens
from services.bot.local_bot.keyboards import (
    build_user_menu,
    build_admin_menu,
    login_kb,
)
from services.bot.local_bot.fsm import fsm

common_router = Router()


def _role(uid: str):
    u = tokens.get(uid)
    return u.get("role") if u and u.get("token") else None


# ================================================================
# ЕДИНОЕ МЕНЮ ДЛЯ ВСЕХ
# ================================================================
async def show_unified_menu(bot, chat_id, uid):
    f = fsm(uid)
    role = _role(uid)

    if role == "admin":
        await f.show_menu(bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    elif role == "student":
        await f.show_menu(bot, chat_id, "🎓 Меню студента", build_user_menu())
    else:
        await f.show_menu(bot, chat_id, "👋 Привет! Войдите в систему:", login_kb())


# ================================================================
# ВОЗВРАТ В МЕНЮ
# ================================================================
@common_router.callback_query(lambda c: c.data == "btn_back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    f.clear()
    await show_unified_menu(callback.bot, chat_id, uid)
    await callback.answer()


# ================================================================
# CANCEL
# ================================================================
@common_router.callback_query(lambda c: c.data == "btn_cancel")
async def cb_cancel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    # Удаляем текущее сообщение с кнопкой отмены
    try:
        await callback.message.delete()
    except:
        pass

    # Очищаем все промежуточные сообщения
    await f.clear_prompts(callback.bot, chat_id)

    # Сбрасываем FSM
    f.clear()

    # Сразу показываем меню (без сообщения "Действие отменено")
    await show_unified_menu(callback.bot, chat_id, uid)
    await callback.answer()


# ================================================================
# RESET
# ================================================================
@common_router.message(Command("reset"))
async def reset(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    # Удаляем команду /reset
    try:
        await message.delete()
    except:
        pass

    # Очищаем промежуточные сообщения
    await f.clear_prompts(message.bot, chat_id)

    # Удаляем старое меню
    st = f.get()
    old_menu_id = st.get("menu_id")
    if old_menu_id:
        try:
            await message.bot.delete_message(chat_id, old_menu_id)
        except:
            pass

    # Сбрасываем FSM
    f.clear()

    # Показываем единое меню
    await show_unified_menu(message.bot, chat_id, uid)
