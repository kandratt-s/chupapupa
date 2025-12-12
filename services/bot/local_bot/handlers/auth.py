# handlers/auth.py
"""
Авторизация, выход, профиль.
"""

import time
import asyncio
from aiogram import Router, types
from aiogram.filters import Command

from services.bot.local_bot.config import BOT_TOKEN
from services.bot.local_bot.storage import tokens, user_info, save_tokens
from services.bot.local_bot.fsm import get_state, set_state, clear_state, delete_prompts
from services.bot.local_bot.keyboards import (
    login_kb,
    build_user_menu,
    build_admin_menu,
    cancel_kb,
    back_to_menu_kb,
)
from services.bot.local_bot.utils import (
    validate_mail,
    hash_password,
    delete_message_safe,
    get_display_name,
)


auth_router = Router()


def is_authenticated(user_id: str) -> bool:
    """Проверка наличия активного токена."""
    u = tokens.get(user_id)
    return bool(u and u.get("token"))


@auth_router.message(Command("start"))
async def start_command(message: types.Message):
    """Точка входа /start."""
    uid = str(message.from_user.id)
    name = get_display_name(uid, tokens, user_info, message.from_user)
    current = tokens.get(uid)

    if is_authenticated(uid):
        if current.get("role") == "admin":
            await message.answer(
                f"👋 {name}, вы авторизованы как админ",
                reply_markup=build_admin_menu(),
            )
        else:
            await message.answer(
                f"👋 {name}, вы авторизованы как студент",
                reply_markup=build_user_menu(),
            )
        return

    await message.answer(
        f"👋 {name}, привет! Я бот для учёта посещаемости.\n\n"
        "Для входа используйте свой email и пароль или admin/admin для входа администратора.",
        reply_markup=login_kb(),
    )


@auth_router.message(Command("reset"))
async def reset_state(message: types.Message):
    """Жёсткий сброс FSM для текущего пользователя."""
    uid = str(message.from_user.id)
    clear_state(uid)
    await message.answer("✅ Состояние сброшено")


@auth_router.callback_query(lambda c: c.data == "btn_login")
async def cb_btn_login(callback: types.CallbackQuery):
    """Начало процесса входа."""
    uid = str(callback.from_user.id)
    clear_state(uid)

    st = {"state": "waiting_email", "ts": time.time(), "prompts": []}
    set_state(uid, st)

    msg = await callback.message.edit_text(
        "📧 Введите email:", reply_markup=cancel_kb()
    )
    st["prompts"].append(msg.message_id)
    set_state(uid, st)

    await callback.answer()


@auth_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state")
    in ("waiting_email", "waiting_password")
)
async def receive_login(message: types.Message):
    """FSM-процесс логина: email → пароль."""
    uid = str(message.from_user.id)
    st = get_state(uid)
    state = st.get("state")

    try:
        await message.delete()
    except Exception:
        pass

    if state == "waiting_email":
        email = message.text.strip()

        # Специальный вход admin/admin
        if email.lower() == "admin":
            st["email"] = "admin"
            st["is_admin"] = True
            st["state"] = "waiting_password"
            await delete_prompts(message.bot, uid, message.chat.id)

            msg = await message.answer(
                "🔑 Введите пароль администратора:",
                reply_markup=cancel_kb(),
            )
            st.setdefault("prompts", []).append(msg.message_id)
            set_state(uid, st)
            return

        if not validate_mail(email):
            err = await message.answer("❌ Некорректный email")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        if email not in user_info:
            err = await message.answer("❌ Пользователь не найден")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        st["email"] = email
        st["state"] = "waiting_password"

        await delete_prompts(message.bot, uid, message.chat.id)
        msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_kb())
        st.setdefault("prompts", []).append(msg.message_id)
        set_state(uid, st)
        return

    if state == "waiting_password":
        password = message.text.strip()
        await delete_prompts(message.bot, uid, message.chat.id)

        # Проверка admin/admin
        if st.get("is_admin"):
            if password != "admin":
                err = await message.answer("❌ Неверный пароль администратора")
                await asyncio.sleep(2)
                await delete_message_safe(err.chat.id, err.message_id)

                msg = await message.answer(
                    "🔑 Введите пароль администратора:",
                    reply_markup=cancel_kb(),
                )
                st.setdefault("prompts", []).append(msg.message_id)
                set_state(uid, st)
                return

            tokens[uid] = {
                "email": "admin",
                "token": f"ADMIN_{uid}_{int(time.time())}",
                "role": "admin",
                "practice_points": 0,
            }
            save_tokens()
            clear_state(uid)

            await message.answer(
                "✅ Вход выполнен\n👑 Роль: администратор",
                reply_markup=build_admin_menu(),
            )
            return

        # Обычный пользователь
        email = st.get("email")
        if not email:
            clear_state(uid)
            err = await message.answer("❌ Ошибка авторизации, начните заново")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        record = user_info.get(email)
        if not record:
            clear_state(uid)
            err = await message.answer("❌ Профиль не найден")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        if record.get("password_hash") != hash_password(password):
            err = await message.answer("❌ Неверный пароль")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)

            msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_kb())
            st.setdefault("prompts", []).append(msg.message_id)
            set_state(uid, st)
            return

        # Берём баллы по email
        email_token = next(
            (t for t in tokens.values() if t.get("email") == email),
            None,
        )
        points = email_token.get("practice_points", 0) if email_token else 0

        tokens[uid] = {
            "email": email,
            "token": f"TOKEN_{uid}_{int(time.time())}",
            "role": record.get("role", "student"),
            "practice_points": points,
        }
        save_tokens()
        clear_state(uid)

        name = record.get("first_name") or get_display_name(
            uid, tokens, user_info, message.from_user
        )

        if tokens[uid]["role"] == "admin":
            await message.answer(
                f"✅ {name}, вход выполнен\n👑 Роль: администратор",
                reply_markup=build_admin_menu(),
            )
        else:
            await message.answer(
                f"✅ {name}, вход выполнен\n🎓 Роль: студент\n⭐ Баллы: {points}",
                reply_markup=build_user_menu(),
            )


@auth_router.callback_query(lambda c: c.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    """Показ профиля пользователя."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.message.edit_text(
            "❌ Сначала авторизуйтесь", reply_markup=login_kb()
        )
        await callback.answer()
        return

    base_token = tokens.get(uid, {})
    email = base_token.get("email")

    if not email:
        await callback.message.edit_text("❌ Профиль не найден (нет email)")
        await callback.answer()
        return

    user = next((t for t in tokens.values() if t.get("email") == email), None)
    if not user:
        await callback.message.edit_text("❌ Профиль не найден")
        await callback.answer()
        return

    role = user.get("role", "student")
    points = user.get("practice_points", 0)

    if role == "admin":
        text = f"👤 Профиль администратора\n📧 {email}"
    else:
        text = f"👤 Профиль студента\n📧 {email}\n⭐ Баллы: {points}"

    await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()


@auth_router.callback_query(lambda c: c.data == "btn_logout")
async def cb_logout(callback: types.CallbackQuery):
    """Выход пользователя и очистка токена."""
    uid = str(callback.from_user.id)
    tokens.pop(uid, None)
    save_tokens()
    clear_state(uid)

    await callback.message.edit_text("👋 Вы вышли из аккаунта", reply_markup=login_kb())
    await callback.answer()
