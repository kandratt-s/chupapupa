import asyncio
from aiogram import Router, types
from aiogram.filters import Command

from services.bot.gateway_bot.fsm.fsm import fsm
from services.bot.gateway_bot.keyboards import (
    build_admin_menu,
    build_user_menu,
    login_kb,
    cancel_kb,
)
from services.bot.gateway_bot.utils.utils import delete_message_safe
from services.bot.gateway_bot.api.auth import api_login
from services.bot.gateway_bot.api.api import api_get_user

auth_router = Router()


# ================================================================
# START
# ================================================================
@auth_router.message(Command("start"))
async def start(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    await f.clear_prompts(message.bot, chat_id)

    st = f.get()
    old_menu = st.get("menu_id")
    if old_menu:
        try:
            await message.bot.delete_message(chat_id, old_menu)
        except:
            pass

    token = st.get("token")
    role = st.get("role")

    if token and role == "admin":
        await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
        return

    if token and role == "student":
        await f.show_menu(message.bot, chat_id, "🎓 Меню студента", build_user_menu())
        return

    f.clear()
    await f.show_menu(message.bot, chat_id, "👋 Войдите в систему:", login_kb())


# ================================================================
# LOGIN
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_login")
async def cb_login(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    f.clear()
    f.set(state="login_email")

    try:
        await callback.message.delete()
    except:
        pass

    msg = await callback.bot.send_message(
        chat_id, "📧 Введите email:", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)
    await callback.answer()


@auth_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "login_email"
)
async def login_email(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    email = message.text.strip()
    f.set(login_email=email, state="login_password")

    msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)


@auth_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "login_password"
)
async def login_password(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    password = message.text.strip()
    email = f.get().get("login_email")

    # 🔥 API LOGIN
    login_data = await api_login(email=email, password=password, telegram_id=uid)

    if not login_data:
        err = await message.answer("❌ Неверный логин или пароль")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    token = login_data["access_token"]
    role = login_data["role"]
    backend_user_id = login_data["user_id"]

    # 🔥 Получаем профиль
    profile = await api_get_user(token, backend_user_id)

    first_name = profile.get("first_name", "")
    practice_points = profile.get("practice_points", 0)

    # Сохраняем сессию
    f.set(
        token=token,
        role=role,
        email=email,
        backend_user_id=backend_user_id,
        practice_points=practice_points,
    )

    await f.clear_prompts(message.bot, chat_id)
    f.clear(keep=("token", "role", "email", "backend_user_id", "practice_points"))

    await f.log(message.bot, chat_id, f"✅ Добро пожаловать, {first_name}!")

    if role == "admin":
        await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    else:
        await f.show_menu(message.bot, chat_id, "🎓 Меню студента", build_user_menu())


# ================================================================
# PROFILE
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    st = f.get()
    token = st.get("token")
    backend_user_id = st.get("backend_user_id")

    profile = await api_get_user(token, backend_user_id)

    email = profile.get("email", "—")
    role = st.get("role")
    points = profile.get("practice_points", 0)

    f.set(practice_points=points)

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
# LOGOUT
# ================================================================
@auth_router.callback_query(lambda c: c.data == "btn_logout")
async def cb_logout(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    f.clear()

    try:
        await callback.message.delete()
    except:
        pass

    await f.log(callback.bot, chat_id, "👋 Вы вышли из системы")
    await f.show_menu(callback.bot, chat_id, "👋 Войдите в систему:", login_kb())
    await callback.answer()
