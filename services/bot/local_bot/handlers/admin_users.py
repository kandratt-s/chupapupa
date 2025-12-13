"""
Админ: создание пользователей.
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

    # Удаляем меню
    try:
        await callback.message.delete()
    except:
        pass

    msg = await callback.bot.send_message(
        chat_id, "📧 Введите email нового пользователя:", reply_markup=cancel_kb()
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

    st = f.get()
    if st.get("state") != "reg_email":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    email = message.text.strip()

    if not validate_mail(email):
        err = await message.answer("❌ Некорректный email")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    if email in user_info:
        err = await message.answer("❌ Такой email уже зарегистрирован")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
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

    st = f.get()
    if st.get("state") != "reg_firstname":
        return

    if message.text and message.text.startswith("/"):
        return

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

    st = f.get()
    if st.get("state") != "reg_lastname":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    lastname = message.text.strip()
    f.set(lastname=lastname, state="reg_role")
    await f.clear_prompts(message.bot, chat_id)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🎓 Студент", callback_data="reg_role:student")],
            [types.InlineKeyboardButton(text="👑 Администратор", callback_data="reg_role:admin")],
            [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")],
        ]
    )

    msg = await message.answer("🎭 Выберите роль:", reply_markup=kb)
    f.add_prompt(msg.message_id)


# ---------------- ROLE ----------------
@admin_users_router.callback_query(lambda c: c.data.startswith("reg_role:"))
async def reg_role(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    st = f.get()
    if st.get("state") != "reg_role":
        await callback.answer()
        return

    role = callback.data.split(":")[1]
    f.set(role=role, state="reg_password")

    await f.clear_prompts(callback.bot, chat_id)

    msg = await callback.bot.send_message(
        chat_id, "🔑 Введите пароль:", reply_markup=cancel_kb()
    )
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

    st = f.get()
    if st.get("state") != "reg_password":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    pwd = message.text.strip()

    if not validate_password(pwd):
        err = await message.answer("❌ Слабый пароль (мин. 8 символов, буквы, цифры, спецсимволы)")
        await asyncio.sleep(1.5)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    f.set(password=pwd)

    # Если админ — без фото
    if st.get("role") == "admin":
        await create_user_final(uid, message, with_photo=False)
        return

    # Если студент — нужно фото
    f.set(state="reg_photo")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer("📸 Отправьте фото пользователя:", reply_markup=cancel_kb())
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
    if st.get("state") != "reg_photo":
        return

    try:
        await message.delete()
    except:
        pass

    ensure_photos_dir()

    email = st.get("email")
    filename = f"{email}_{int(time.time())}_base.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

    photo = message.photo[-1]
    file_id = photo.file_id

    # Скачиваем фото
    try:
        file_obj = await message.bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"

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
            await delete_message_safe(chat_id, err.message_id, message.bot)
            return

    f.set(photo_path=path, photo_id=file_id)
    await create_user_final(uid, message, with_photo=True)


# ================================================================
# ФИНАЛИЗАЦИЯ СОЗДАНИЯ
# ================================================================
async def create_user_final(admin_uid: str, message: types.Message, with_photo: bool):
    chat_id = message.chat.id
    f = fsm(admin_uid)
    st = f.get()

    email = st.get("email")
    firstname = st.get("firstname")
    lastname = st.get("lastname")
    role = st.get("role")
    pwd = st.get("password")
    photo_path = st.get("photo_path") if with_photo else None
    photo_id = st.get("photo_id") if with_photo else None

    # Создаём пользователя
    user_info[email] = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password_hash": hash_password(pwd),
        "role": role,
        "student_photo_path": photo_path,
        "student_photo_id": photo_id,
    }
    save_user_info()

    await f.clear_prompts(message.bot, chat_id)
    f.clear()

    role_text = "👑 Администратор" if role == "admin" else "🎓 Студент"

    # ЛОГ + МЕНЮ
    await f.log(
        message.bot,
        chat_id,
        f"✅ Пользователь создан:\n{firstname} {lastname}\n📧 {email}\n{role_text}",
    )
    await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())

# ================================================================
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ================================================================
@admin_users_router.callback_query(lambda c: c.data == "btn_list_users")
async def cb_list_users(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    f = fsm(uid)
    f.clear()
    f.set(filter="all", page=0)

    await show_users(callback.message, uid)
    await callback.answer()


async def show_users(message: types.Message, uid: str):
    f = fsm(uid)
    st = f.get()

    filter_mode = st.get("filter", "all")
    page = st.get("page", 0)

    # Собираем всех пользователей
    users = []
    for email, data in user_info.items():
        users.append({
            "email": email,
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "role": data.get("role", "student"),
        })

    # Фильтруем
    if filter_mode == "students":
        users = [u for u in users if u["role"] == "student"]
    elif filter_mode == "admins":
        users = [u for u in users if u["role"] == "admin"]

    if not users:
        try:
            await message.edit_text("📭 Нет пользователей", reply_markup=back_to_menu_kb())
        except:
            pass
        return

    # Пагинация
    per_page = 6
    total_pages = (len(users) - 1) // per_page + 1
    page = max(0, min(page, total_pages - 1))
    f.set(page=page)

    start = page * per_page
    chunk = users[start : start + per_page]

    rows = []
    for u in chunk:
        role_icon = "👑" if u["role"] == "admin" else "🎓"
        name = f"{u['first_name']} {u['last_name']}".strip() or u["email"]
        rows.append(
            [types.InlineKeyboardButton(
                text=f"{role_icon} {name}",
                callback_data=f"user_card:{u['email']}"
            )]
        )

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️", callback_data="users_prev"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton(text="➡️", callback_data="users_next"))

    filter_row = [
        types.InlineKeyboardButton(text="🔵 Все", callback_data="users_filter:all"),
        types.InlineKeyboardButton(text="🎓 Студенты", callback_data="users_filter:students"),
        types.InlineKeyboardButton(text="👑 Админы", callback_data="users_filter:admins"),
    ]

    rows_final = rows.copy()
    if nav:
        rows_final.append(nav)
    rows_final.append(filter_row)
    rows_final.append([types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")])

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows_final)

    try:
        await message.edit_text("👥 Пользователи:", reply_markup=kb)
    except:
        pass


# Пагинация
@admin_users_router.callback_query(lambda c: c.data in ("users_prev", "users_next"))
async def cb_users_nav(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    f = fsm(uid)
    st = f.get()

    if callback.data == "users_prev":
        f.set(page=st.get("page", 0) - 1)
    else:
        f.set(page=st.get("page", 0) + 1)

    await show_users(callback.message, uid)
    await callback.answer()


# Фильтры
@admin_users_router.callback_query(lambda c: c.data.startswith("users_filter:"))
async def cb_users_filter(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    mode = callback.data.split(":")[1]

    f = fsm(uid)
    f.set(filter=mode, page=0)

    await show_users(callback.message, uid)
    await callback.answer()


# ================================================================
# КАРТОЧКА ПОЛЬЗОВАТЕЛЯ
# ================================================================
@admin_users_router.callback_query(lambda c: c.data.startswith("user_card:"))
async def cb_user_card(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    email = callback.data.split(":", 1)[1]
    user = user_info.get(email)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return

    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    role = user.get("role", "student")
    role_text = "👑 Администратор" if role == "admin" else "🎓 Студент"

    # Ищем баллы в tokens
    points = 0
    for tid, tdata in tokens.items():
        if tdata.get("email") == email:
            points = tdata.get("practice_points", 0)
            break

    text = (
        f"👤 {first_name} {last_name}\n\n"
        f"📧 Email: {email}\n"
        f"🎭 Роль: {role_text}\n"
        f"⭐️ Баллы: {points}"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"user_delete:{email}")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_list_users")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ================================================================
# УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ================================================================
@admin_users_router.callback_query(lambda c: c.data.startswith("user_delete:"))
async def cb_user_delete(callback: types.CallbackQuery):
    email = callback.data.split(":", 1)[1]

    user = user_info.get(email)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return

    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or email

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"user_delete_confirm:{email}")],
            [types.InlineKeyboardButton(text="◀️ Отмена", callback_data=f"user_card:{email}")],
        ]
    )

    await callback.message.edit_text(f"❗️ Удалить пользователя?\n{name}", reply_markup=kb)
    await callback.answer()


@admin_users_router.callback_query(lambda c: c.data.startswith("user_delete_confirm:"))
async def cb_user_delete_confirm(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    email = callback.data.split(":", 1)[1]

    user = user_info.get(email)
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() if user else email

    # Удаляем из user_info
    if email in user_info:
        del user_info[email]
        save_user_info()

    # Удаляем токен
    to_delete = [k for k, v in tokens.items() if v.get("email") == email]
    for k in to_delete:
        del tokens[k]
    if to_delete:
        save_tokens()

    f = fsm(uid)

    try:
        await callback.message.delete()
    except:
        pass

    await f.log(callback.bot, chat_id, f"🗑 Пользователь удалён:\n{name}")
    await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    await callback.answer()
