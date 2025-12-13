# handlers/admin_users.py
"""
Админ: создание пользователей, список студентов, просмотр, удаление.
Новый стиль: единый FSM, чистые сообщения, исчезающие ошибки.
"""

import time
import asyncio
import os
import httpx
from aiogram import Router, types

from services.bot.local_bot.storage import (
    tokens,
    user_info,
    save_user_info,
    save_tokens,
)
from services.bot.local_bot.fsm import fsm
from services.bot.local_bot.keyboards import (
    cancel_kb,
    back_to_menu_kb,
    build_admin_menu,
)
from services.bot.local_bot.utils import (
    validate_mail,
    validate_password,
    ensure_photos_dir,
    delete_message_safe,
    hash_password,
)
from services.bot.local_bot.config import PHOTOS_DIR

admin_users_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_admin(uid: str) -> bool:
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


# ================================================================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# ================================================================
@admin_users_router.callback_query(lambda c: c.data == "btn_admin_register")
async def cb_admin_register(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    f = fsm(uid)
    f.clear()
    f.set(state="reg_email")

    msg = await callback.message.answer(
        "📧 Введите email нового пользователя:", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)

    await callback.answer()


# ---------------- EMAIL ----------------
@admin_users_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "reg_email"
)
async def reg_email(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    email = message.text.strip()

    if not validate_mail(email):
        err = await message.answer("❌ Некорректный email")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id)
        return

    if email in user_info:
        err = await message.answer("❌ Такой email уже зарегистрирован")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id)
        return

    f.set(email=email, state="reg_firstname")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer("👤 Введите имя:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)


# ---------------- FIRST NAME ----------------
@admin_users_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "reg_firstname"
)
async def reg_firstname(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    firstname = message.text.strip()
    f.set(firstname=firstname, state="reg_lastname")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer("👤 Введите фамилию:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)


# ---------------- LAST NAME ----------------
@admin_users_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "reg_lastname"
)
async def reg_lastname(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    lastname = message.text.strip()
    f.set(lastname=lastname, state="reg_role")
    await f.clear_prompts(message.bot, chat_id)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🎓 Студент", callback_data="reg_role:student"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="👑 Администратор", callback_data="reg_role:admin"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отменить", callback_data="btn_cancel"
                )
            ],
        ]
    )

    msg = await message.answer("Выберите роль:", reply_markup=kb)
    f.add_prompt(msg.message_id)


# ---------------- ROLE ----------------
@admin_users_router.callback_query(lambda c: c.data.startswith("reg_role:"))
async def reg_role(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    role = callback.data.split(":")[1]
    f.set(role=role, state="reg_password")

    await f.clear_prompts(callback.bot, chat_id)

    msg = await callback.message.answer("🔑 Введите пароль:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)

    await callback.answer()


# ---------------- PASSWORD ----------------
@admin_users_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "reg_password"
)
async def reg_password(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    try:
        await message.delete()
    except:
        pass

    pwd = message.text.strip()

    if not validate_password(pwd):
        err = await message.answer("❌ Пароль слишком слабый")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id)
        return

    f.set(password=pwd)

    # Если админ — фото не нужно
    if f.get().get("role") == "admin":
        await create_admin_user(uid, message)
        return

    # Если студент — фото обязательно
    f.set(state="reg_photo")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer(
        "📸 Отправьте фото пользователя:", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)


# ---------------- PHOTO (STUDENT) ----------------
@admin_users_router.message(
    lambda m: m.photo and fsm(str(m.from_user.id)).get().get("state") == "reg_photo"
)
async def reg_photo(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)
    st = f.get()

    try:
        await message.delete()
    except:
        pass

    ensure_photos_dir()

    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]
    role = st["role"]
    pwd = st["password"]

    filename = f"{email}_{int(time.time())}_base.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

    photo = message.photo[-1]
    file_id = photo.file_id

    # Скачиваем фото
    try:
        file_obj = await message.bot.get_file(file_id)
        url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(path, "wb") as f_out:
                f_out.write(resp.content)
    except:
        try:
            await photo.download(destination_file=path)
        except:
            err = await message.answer("❌ Не удалось сохранить фото")
            await asyncio.sleep(1.2)
            await delete_message_safe(chat_id, err.message_id)
            return

    # Создаём пользователя
    user_info[email] = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password_hash": hash_password(pwd),
        "role": role,
        "student_photo_path": path,
        "student_photo_id": file_id,
    }
    save_user_info()

    f.clear()

    await f.show_menu(
        message.bot,
        chat_id,
        f"✅ Пользователь создан:\n{firstname} {lastname}\n📧 {email}\n👤 Роль: Студент",
        build_admin_menu(),
    )


# ================================================================
# СОЗДАНИЕ АДМИНА (без фото)
# ================================================================
async def create_admin_user(uid: str, message: types.Message):
    chat_id = message.chat.id
    f = fsm(uid)
    st = f.get()

    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]
    pwd = st["password"]

    user_info[email] = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password_hash": hash_password(pwd),
        "role": "admin",
        "student_photo_path": None,
        "student_photo_id": None,
    }
    save_user_info()

    f.clear()

    await f.show_menu(
        message.bot,
        chat_id,
        f"✅ Администратор создан:\n{firstname} {lastname}\n📧 {email}\n👑 Роль: Администратор",
        build_admin_menu(),
    )
