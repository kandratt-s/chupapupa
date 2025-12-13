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

    # Удаляем команду /start
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

    # Полный сброс FSM
    f.clear()

    # Определяем роль и токен
    user_data = tokens.get(uid, {})
    role = user_data.get("role")
    token = user_data.get("token")

    # ЕДИНОЕ МЕНЮ (без приветствий с именем!)
    if role == "admin" and token:
        await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    elif role == "student" and token:
        await f.show_menu(message.bot, chat_id, "🎓 Меню студента", build_user_menu())
    else:
        await f.show_menu(message.bot, chat_id, "👋 Войдите в систему:", login_kb())


# ================================================================
# ПРОФИЛЬ
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    user_data = tokens.get(uid, {})
    email = user_data.get("email", "—")
    role = user_data.get("role", "—")
    points = user_data.get("practice_points", 0)

    role_text = "👑 Администратор" if role == "admin" else "🎓 Студент"

    text = (
        f"👤 Профиль\n\n"
        f"📧 Email: {email}\n"
        f"🎭 Роль: {role_text}\n"
        f"⭐️ Баллы практики: {points}"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ]
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ================================================================
# ВЫХОД
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_logout")
async def cb_logout(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    # Удаляем токен (но сохраняем данные)
    if uid in tokens:
        tokens[uid]["token"] = None

    from services.bot.local_bot.storage import save_tokens

    save_tokens()

    f.clear()

    try:
        await callback.message.delete()
    except:
        pass

    await f.log(callback.bot, chat_id, "👋 Вы вышли из системы")
    await f.show_menu(callback.bot, chat_id, "👋 Войдите в систему:", login_kb())
    await callback.answer()
