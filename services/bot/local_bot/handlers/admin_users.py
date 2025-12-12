# handlers/admin_users.py
"""
Админ: создание пользователей, список студентов, просмотр, удаление.
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
    load_applications,
    save_applications,
)

from services.bot.local_bot.fsm import (
    get_state,
    set_state,
    clear_state,
    delete_prompts,
)

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

admin_users_router = Router()


def is_admin(uid: str) -> bool:
    """Проверка роли администратора."""
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


# ===============================================================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# ===============================================================


@admin_users_router.callback_query(lambda c: c.data == "btn_admin_register")
async def cb_admin_register(callback: types.CallbackQuery):
    """Начало регистрации нового пользователя."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    clear_state(uid)

    st = {"state": "reg_email", "prompts": [], "ts": time.time()}
    set_state(uid, st)

    msg = await callback.message.edit_text(
        "📧 Введите email нового пользователя:", reply_markup=cancel_kb()
    )
    st["prompts"].append(msg.message_id)
    set_state(uid, st)

    await callback.answer()


@admin_users_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "reg_email"
)
async def reg_email(message: types.Message):
    """Ввод email."""
    uid = str(message.from_user.id)
    email = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    if not validate_mail(email):
        err = await message.answer("❌ Некорректный email")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    if email in user_info:
        err = await message.answer("❌ Такой email уже зарегистрирован")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = get_state(uid)
    st["email"] = email
    st["state"] = "reg_firstname"
    set_state(uid, st)

    msg = await message.answer("👤 Введите имя:", reply_markup=cancel_kb())
    st["prompts"].append(msg.message_id)
    set_state(uid, st)


@admin_users_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "reg_firstname"
)
async def reg_firstname(message: types.Message):
    """Ввод имени."""
    uid = str(message.from_user.id)
    firstname = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = get_state(uid)
    st["firstname"] = firstname
    st["state"] = "reg_lastname"
    set_state(uid, st)

    msg = await message.answer("👤 Введите фамилию:", reply_markup=cancel_kb())
    st["prompts"].append(msg.message_id)
    set_state(uid, st)


@admin_users_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "reg_lastname"
)
async def reg_lastname(message: types.Message):
    """Ввод фамилии."""
    uid = str(message.from_user.id)
    lastname = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = get_state(uid)
    st["lastname"] = lastname
    st["state"] = "reg_role"
    set_state(uid, st)

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

    await message.answer("Выберите роль:", reply_markup=kb)


@admin_users_router.callback_query(lambda c: c.data.startswith("reg_role:"))
async def reg_role(callback: types.CallbackQuery):
    """Выбор роли."""
    uid = str(callback.from_user.id)
    role = callback.data.split(":")[1]

    st = get_state(uid)
    st["role"] = role

    # Админ — без фото
    if role == "admin":
        st["state"] = "reg_finish_admin"
        set_state(uid, st)

        await callback.message.edit_text("🔑 Введите пароль:", reply_markup=cancel_kb())
        await callback.answer()
        return

    # Студент — обычный поток
    st["state"] = "reg_password"
    set_state(uid, st)

    await callback.message.edit_text("🔑 Введите пароль:", reply_markup=cancel_kb())
    await callback.answer()


@admin_users_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "reg_finish_admin"
)
async def reg_finish_admin(message: types.Message):
    """Завершение регистрации администратора (без фото)."""
    uid = str(message.from_user.id)
    pwd = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    if not validate_password(pwd):
        err = await message.answer("❌ Пароль слишком слабый")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = get_state(uid)
    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]

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

    clear_state(uid)

    await message.answer(
        f"✅ Администратор создан:\n"
        f"{firstname} {lastname}\n"
        f"📧 {email}\n"
        f"👑 Роль: Администратор",
        reply_markup=build_admin_menu(),
    )


@admin_users_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "reg_password"
)
async def reg_password(message: types.Message):
    """Ввод пароля студента."""
    uid = str(message.from_user.id)
    pwd = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    if not validate_password(pwd):
        err = await message.answer("❌ Пароль слишком слабый")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = get_state(uid)
    st["password"] = pwd
    st["state"] = "reg_photo"
    set_state(uid, st)

    await message.answer("📸 Отправьте фото пользователя:", reply_markup=cancel_kb())


@admin_users_router.message(
    lambda m: m.photo and get_state(str(m.from_user.id)).get("state") == "reg_photo"
)
async def reg_photo(message: types.Message):
    """Регистрация студента с фото."""
    uid = str(message.from_user.id)
    st = get_state(uid)

    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]
    role = st["role"]
    pwd = st["password"]

    ensure_photos_dir()
    photo = message.photo[-1]
    file_id = photo.file_id
    filename = f"{email}_{int(time.time())}_base.jpg"
    path = os.path.join("photos", filename)

    try:
        file_obj = await message.bot.get_file(file_id)
        url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
    except Exception:
        try:
            await photo.download(destination_file=path)
        except Exception:
            await message.answer("❌ Не удалось сохранить фото")
            return

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

    clear_state(uid)

    await message.answer(
        f"✅ Пользователь создан:\n"
        f"{firstname} {lastname}\n"
        f"📧 {email}\n"
        f"👤 Роль: {'Администратор' if role == 'admin' else 'Студент'}",
        reply_markup=build_admin_menu(),
    )


# ===============================================================
# СПИСОК СТУДЕНТОВ
# ===============================================================

STUDENTS_PAGE_SIZE = 10


@admin_users_router.callback_query(lambda c: c.data == "btn_admin_students")
async def cb_admin_students(callback: types.CallbackQuery):
    """Показ списка студентов."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    students = [info for info in user_info.values() if info.get("role") == "student"]

    if not students:
        await callback.message.edit_text(
            "📭 Студентов нет", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    st = {"state": "students_list", "students": students, "page": 0}
    set_state(uid, st)

    await show_students_page(callback.message, uid, 0)
    await callback.answer()


async def show_students_page(message: types.Message, uid: str, page: int):
    """Показ страницы списка студентов."""
    st = get_state(uid)
    students = st.get("students", [])

    total = len(students)
    max_page = (total - 1) // STUDENTS_PAGE_SIZE

    page = max(0, min(page, max_page))

    start = page * STUDENTS_PAGE_SIZE
    end = min(start + STUDENTS_PAGE_SIZE, total)
    chunk = students[start:end]

    text = "👥 Список студентов:\n"

    buttons = []
    for s in chunk:
        name = f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
        email = s.get("email")

        buttons.append(
            [
                types.InlineKeyboardButton(
                    text=f"📄 {name}", callback_data=f"student_open:{email}"
                )
            ]
        )

    nav_row = []
    if page > 0:
        nav_row.append(
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="students_prev")
        )
    if page < max_page:
        nav_row.append(
            types.InlineKeyboardButton(text="Вперёд ➡️", callback_data="students_next")
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append(
        [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.edit_text(text, reply_markup=kb)

    st["page"] = page
    set_state(uid, st)


@admin_users_router.callback_query(lambda c: c.data == "students_prev")
async def students_prev(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)
    await show_students_page(callback.message, uid, st.get("page", 0) - 1)
    await callback.answer()


@admin_users_router.callback_query(lambda c: c.data == "students_next")
async def students_next(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)
    await show_students_page(callback.message, uid, st.get("page", 0) + 1)
    await callback.answer()


# ===============================================================
# ПРОСМОТР И УДАЛЕНИЕ СТУДЕНТА
# ===============================================================


@admin_users_router.callback_query(lambda c: c.data.startswith("student_open:"))
async def student_open(callback: types.CallbackQuery):
    """Показ карточки студента."""
    uid = str(callback.from_user.id)
    email = callback.data.split(":")[1]

    student = user_info.get(email)
    if not student:
        await callback.answer("❌ Студент не найден")
        return

    name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()

    text = f"👤 Студент:\n" f"{name}\n" f"📧 {email}\n" f"🎓 Роль: студент\n"

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"student_delete:{email}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ Назад", callback_data="btn_admin_students"
                )
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@admin_users_router.callback_query(lambda c: c.data.startswith("student_delete:"))
async def student_delete(callback: types.CallbackQuery):
    """Удаление студента."""
    uid = str(callback.from_user.id)
    email = callback.data.split(":")[1]

    user_info.pop(email, None)
    save_user_info()

    to_delete = [k for k, v in tokens.items() if v.get("email") == email]
    for k in to_delete:
        tokens.pop(k, None)
    save_tokens()

    apps = load_applications()
    apps["applications"] = [
        a for a in apps.get("applications", []) if a.get("user_email") != email
    ]
    save_applications(apps)

    await callback.message.edit_text(
        f"✅ Студент {email} удалён", reply_markup=back_to_menu_kb()
    )
    await callback.answer()
