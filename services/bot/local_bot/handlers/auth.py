import time
import asyncio
from aiogram import Router, types
from aiogram.filters import Command

from services.bot.local_bot.storage import tokens, user_info, save_tokens
from services.bot.local_bot.keyboards import (
    build_admin_menu,
    build_user_menu,
    login_kb,
    cancel_kb,
)
from services.bot.local_bot.fsm import fsm
from services.bot.local_bot.utils import hash_password, delete_message_safe

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
# ВХОД В СИСТЕМУ
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_login")
async def cb_login(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    f.clear()
    f.set(state="login_email")

    # Удаляем меню
    try:
        await callback.message.delete()
    except:
        pass

    msg = await callback.bot.send_message(
        chat_id, "📧 Введите ваш email:", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)
    await callback.answer()


# ---------------- LOGIN EMAIL ----------------
@auth_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "login_email"
)
async def login_email(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    st = f.get()
    if st.get("state") != "login_email":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    email = message.text.strip().lower()

    # Проверяем существует ли пользователь
    if email not in user_info:
        err = await message.answer("❌ Пользователь не найден")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    f.set(login_email=email, state="login_password")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)


# ---------------- LOGIN PASSWORD ----------------
@auth_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "login_password"
)
async def login_password(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    st = f.get()
    if st.get("state") != "login_password":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    password = message.text.strip()
    email = st.get("login_email")

    # Проверяем пароль
    user = user_info.get(email, {})
    stored_hash = user.get("password_hash")

    if not stored_hash or hash_password(password) != stored_hash:
        err = await message.answer("❌ Неверный пароль")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    # Успешная авторизация
    role = user.get("role", "student")
    token = f"{role.upper()}_{uid}_{int(time.time())}"

    # Сохраняем токен
    tokens[uid] = {
        "email": email,
        "token": token,
        "role": role,
        "practice_points": tokens.get(uid, {}).get("practice_points", 0),
    }
    save_tokens()

    await f.clear_prompts(message.bot, chat_id)
    f.clear()

    # ЛОГ + МЕНЮ
    first_name = user.get("first_name", "")
    await f.log(message.bot, chat_id, f"✅ Добро пожаловать, {first_name}!")

    if role == "admin":
        await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    else:
        await f.show_menu(message.bot, chat_id, "🎓 Меню студента", build_user_menu())

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
