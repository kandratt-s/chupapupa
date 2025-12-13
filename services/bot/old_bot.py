# ================================================================
# bot_local.py — Часть 1/4
# Базовая инфраструктура: импорты, хранилища, меню, базовые хелперы
# ================================================================

import asyncio
import time
import os
from turtle import st
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from services.bot.local_bot.config import (
    BOT_TOKEN,
    USER_TOKENS_PATH,
    USER_INFO_PATH,
    USER_STATES_PATH,
    APPLICATIONS_PATH,
    EVENTS_PATH,
    PHOTOS_DIR,
)
from services.bot.Bot_local.core.utils import (
    load,
    save,
    validate_mail,
    validate_password,
    get_display_name,
    clear_user_state,
    ensure_photos_dir,
    hash_password,
)

# Локальные хранилища. Это моя псевдо-БД.
tokens = (
    load(USER_TOKENS_PATH) or {}
)  # авторизованные пользователи (по Telegram user_id)
user_info = load(USER_INFO_PATH) or {}  # данные учёток (email → профиль)
user_states = load(USER_STATES_PATH) or {}  # FSM-состояния пользователей

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cancel_btn = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")]
    ]
)


def is_authenticated(user_id: str) -> bool:
    """Минимальная проверка — есть ли у пользователя активный токен."""
    u = tokens.get(user_id)
    return bool(u and u.get("token"))


async def delete_message_safe(chat_id: int, message_id: int):
    """Тихо удаляю сообщение. Если не получилось — просто игнорирую."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def build_user_menu(user_id: str) -> types.InlineKeyboardMarkup:
    """Главное меню студента."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📅 Мероприятия", callback_data="btn_events"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📊 Мои заявки", callback_data="btn_my_applications"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="👤 Профиль", callback_data="btn_profile"
                )
            ],
            [types.InlineKeyboardButton(text="🚪 Выйти", callback_data="btn_logout")],
        ]
    )


def build_admin_menu(user_id: str) -> types.InlineKeyboardMarkup:
    """Главное меню администратора."""
    apps = load(APPLICATIONS_PATH) or {}
    applications = apps.get("applications", [])
    pending = len([a for a in applications if a.get("status") == "pending"])

    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="➕ Создать мероприятие", callback_data="btn_create_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📋 Список мероприятий", callback_data="btn_list_events"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=f"📥 Рассмотреть заявки ({pending})",
                    callback_data="btn_review_applications",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🏁 Закончить мероприятие", callback_data="btn_finish_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="👥 Создать пользователя", callback_data="btn_admin_register"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="👥 Студенты", callback_data="btn_admin_students"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="👤 Профиль", callback_data="btn_profile"
                )
            ],
            [types.InlineKeyboardButton(text="🚪 Выйти", callback_data="btn_logout")],
        ]
    )


@dp.message(Command("start"))
async def start_command(message: types.Message):
    """
    /start — стандартная точка входа.
    Если пользователь уже авторизован — сразу кидаю его в меню с нужной ролью.
    """
    uid = str(message.from_user.id)
    name = get_display_name(uid, tokens, user_info, message.from_user)
    current = tokens.get(uid)

    if is_authenticated(uid):
        if current.get("role") == "admin":
            await message.answer(
                f"👋 {name}, вы авторизованы как админ",
                reply_markup=build_admin_menu(uid),
            )
        else:
            await message.answer(
                f"👋 {name}, вы авторизованы как студент",
                reply_markup=build_user_menu(uid),
            )
        return

    start_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
        ]
    )
    await message.answer(
        f"👋 {name}, привет! Я бот для учёта посещаемости.\n\n"
        "Для входа используйте свой email и пароль или admin/admin для входа администратора.",
        reply_markup=start_kb,
    )


@dp.message(Command("reset"))
async def reset_state(message: types.Message):
    """Жёсткий сброс состояния FSM для текущего пользователя."""
    uid = str(message.from_user.id)
    clear_user_state(user_states, uid)
    await message.answer("✅ Состояние сброшено")


@dp.callback_query(lambda c: c.data == "btn_back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    """Универсальная кнопка «назад в меню»."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        start_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
            ]
        )
        await callback.message.edit_text("❌ Вы не авторизованы", reply_markup=start_kb)
        await callback.answer()
        return

    role = tokens.get(uid, {}).get("role", "student")
    name = get_display_name(uid, tokens, user_info, callback.from_user)

    if role == "admin":
        await callback.message.edit_text(
            f"📋 Главное меню администратора, {name}",
            reply_markup=build_admin_menu(uid),
        )
    else:
        await callback.message.edit_text(
            f"📋 Главное меню, {name}", reply_markup=build_user_menu(uid)
        )

    await callback.answer()

# ================================================================
# bot_local.py — Часть 2/4
# Авторизация: admin/admin, обычные пользователи, профиль, выход
# ================================================================


@dp.callback_query(lambda c: c.data == "btn_login")
async def cb_btn_login(callback: types.CallbackQuery):
    """
    Пользователь нажал «Войти».
    Я сбрасываю его состояние и прошу ввести email.
    Служебные сообщения удаляются, чтобы не засорять чат.
    """
    uid = str(callback.from_user.id)

    clear_user_state(user_states, uid)

    user_states[uid] = {"state": "waiting_email", "ts": time.time()}
    save(user_states, USER_STATES_PATH)

    msg = await callback.message.edit_text("📧 Введите email:", reply_markup=cancel_btn)
    user_states[uid]["prompt"] = msg.message_id
    save(user_states, USER_STATES_PATH)

    await callback.answer()


async def delete_prompts(uid: str, chat_id: int):
    st = user_states.get(uid, {})
    prompts = st.get("prompts", [])
    for mid in prompts:
        await delete_message_safe(chat_id, mid)
    st["prompts"] = []
    user_states[uid] = st
    save(user_states, USER_STATES_PATH)


# ---------------------------------------------------------------
# FSM: обработка email и пароля
# ---------------------------------------------------------------
@dp.message(
    lambda m: user_states.get(str(m.from_user.id), {}).get("state")
    in ("waiting_email", "waiting_password")
)
async def receive_login(message: types.Message):
    uid = str(message.from_user.id)
    st = user_states.get(uid, {})
    state = st.get("state")

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    # -----------------------------------------------------------
    # Шаг 1 — ввод email
    # -----------------------------------------------------------
    if state == "waiting_email":
        email = message.text.strip()

        # --- Специальный вход администратора ---
        if email.lower() == "admin":
            st["email"] = "admin"
            st["is_admin"] = True
            st["state"] = "waiting_password"

            await delete_prompts(uid, message.chat.id)

            msg = await message.answer(
                "🔑 Введите пароль администратора:", reply_markup=cancel_btn
            )
            st.setdefault("prompts", []).append(msg.message_id)
            save(user_states, USER_STATES_PATH)
            return

        # --- Обычный пользователь ---
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

        await delete_prompts(uid, message.chat.id)

        msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_btn)
        st.setdefault("prompts", []).append(msg.message_id)
        save(user_states, USER_STATES_PATH)
        return

    # -----------------------------------------------------------
    # Шаг 2 — ввод пароля
    # -----------------------------------------------------------
    if state == "waiting_password":
        password = message.text.strip()

        await delete_prompts(uid, message.chat.id)

        # --- Проверка admin/admin ---
        if st.get("is_admin"):
            if password != "admin":
                err = await message.answer("❌ Неверный пароль администратора")
                await asyncio.sleep(2)
                await delete_message_safe(err.chat.id, err.message_id)

                msg = await message.answer(
                    "🔑 Введите пароль администратора:", reply_markup=cancel_btn
                )
                st.setdefault("prompts", []).append(msg.message_id)
                save(user_states, USER_STATES_PATH)
                return

            # успешный вход администратора
            tokens[uid] = {
                "email": "admin",
                "token": f"ADMIN_{uid}_{int(time.time())}",
                "role": "admin",
                "practice_points": 0,
            }
            save(tokens, USER_TOKENS_PATH)
            clear_user_state(user_states, uid)

            await message.answer(
                "✅ Вход выполнен\n👑 Роль: администратор",
                reply_markup=build_admin_menu(uid),
            )
            return

        # --- Обычный пользователь ---
        email = st.get("email")
        if not email:
            clear_user_state(user_states, uid)
            err = await message.answer("❌ Ошибка авторизации, начните заново")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        record = user_info.get(email)
        if not record:
            clear_user_state(user_states, uid)
            err = await message.answer("❌ Профиль не найден")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)
            return

        if record.get("password_hash") != hash_password(password):
            err = await message.answer("❌ Неверный пароль")
            await asyncio.sleep(2)
            await delete_message_safe(err.chat.id, err.message_id)

            msg = await message.answer("🔑 Введите пароль:", reply_markup=cancel_btn)
            st.setdefault("prompts", []).append(msg.message_id)
            save(user_states, USER_STATES_PATH)
            save(user_states, USER_STATES_PATH)
            return

        # ✅ Ищем токен по email — там лежат реальные баллы
        email_token = next(
            (t for t in tokens.values() if t.get("email") == email), None
        )
        points = email_token.get("practice_points", 0) if email_token else 0

        # ✅ Создаём токен по uid (телеграм-id), но с правильными баллами
        tokens[uid] = {
            "email": email,
            "token": f"TOKEN_{uid}_{int(time.time())}",
            "role": record.get("role", "student"),
            "practice_points": points,
        }
        save(tokens, USER_TOKENS_PATH)
        clear_user_state(user_states, uid)

        name = record.get("first_name") or get_display_name(
            uid, tokens, user_info, message.from_user
        )

        if tokens[uid]["role"] == "admin":
            await message.answer(
                f"✅ {name}, вход выполнен\n👑 Роль: администратор",
                reply_markup=build_admin_menu(uid),
            )
        else:
            await message.answer(
                f"✅ {name}, вход выполнен\n🎓 Роль: студент\n⭐ Баллы: {points}",
                reply_markup=build_user_menu(uid),
            )
        return


# ---------------------------------------------------------------
# Профиль
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
            ]
        )
        await callback.message.edit_text("❌ Сначала авторизуйтесь", reply_markup=kb)
        await callback.answer()
        return

    # email из токена по telegram-id
    base_token = tokens.get(uid, {})
    email = base_token.get("email")

    if not email:
        await callback.message.edit_text("❌ Профиль не найден (нет email)")
        await callback.answer()
        return

    # ищем профиль по email
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


# ---------------------------------------------------------------
# Выход
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_logout")
async def cb_logout(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    tokens.pop(uid, None)
    save(tokens, USER_TOKENS_PATH)
    clear_user_state(user_states, uid)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
        ]
    )

    await callback.message.edit_text("👋 Вы вышли из аккаунта", reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Отмена
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_cancel")
async def cb_cancel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    clear_user_state(user_states, uid)

    if is_authenticated(uid):
        role = tokens[uid]["role"]
        if role == "admin":
            await callback.message.edit_text(
                "❌ Действие отменено", reply_markup=build_admin_menu(uid)
            )
        else:
            await callback.message.edit_text(
                "❌ Действие отменено", reply_markup=build_user_menu(uid)
            )
    else:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
            ]
        )
        await callback.message.edit_text("❌ Действие отменено", reply_markup=kb)

    await callback.answer()

# ================================================================
# bot_local.py — Часть 3/4
# Мероприятия, отметка, заявки
# ================================================================


# ---------------------------------------------------------------
# Кнопка «Мероприятия»
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_events")
async def cb_events(callback: types.CallbackQuery):
    """
    Студент открывает список мероприятий.
    Показываю только активные шаблоны.
    """
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
            ]
        )
        await callback.message.edit_text("❌ Сначала авторизуйтесь", reply_markup=kb)
        await callback.answer()
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    active = [
        ev for ev in events if ev.get("is_template") and ev.get("is_active", True)
    ]

    if not active:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.edit_text("📭 Нет активных мероприятий", reply_markup=kb)
        await callback.answer()
        return

    rows = []
    for idx, ev in enumerate(events):
        if ev.get("is_template") and ev.get("is_active", True):
            name = ev.get("event_name", "(без названия)")
            date = ev.get("event_date", "-")
            rows.append(
                [
                    types.InlineKeyboardButton(
                        text=f"{name} — {date}", callback_data=f"view_event:{idx}"
                    )
                ]
            )

    rows.append(
        [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("📅 Активные мероприятия:", reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Просмотр конкретного мероприятия
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("view_event:"))
async def cb_view_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    try:
        idx = int(callback.data.split(":")[1])
    except:
        await callback.answer("❌ Ошибка выбора")
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    if idx < 0 or idx >= len(events):
        await callback.answer("❌ Мероприятие не найдено")
        return

    ev = events[idx]

    name = ev.get("event_name", "(без названия)")
    date = ev.get("event_date", "-")
    desc = ev.get("description", "Нет описания")
    is_prof = ev.get("is_profile", False)

    base_points = 2
    multiplier = 1.5 if is_prof else 0.5
    points = int(base_points * multiplier)

    text = (
        f"📌 {name}\n\n"
        f"📅 Дата: {date}\n"
        f"📝 Описание: {desc}\n"
        f"🎯 Тип: {'профильное' if is_prof else 'непрофильное'}\n"
        f"⭐ Баллы: {points}"
    )

    uid = str(callback.from_user.id)
    role = tokens.get(uid, {}).get("role", "student")

    buttons = []

    if role == "student":
        buttons.append([
            types.InlineKeyboardButton(
                text="✅ Отметиться", callback_data=f"attend_event:{idx}"
            )
        ])

    buttons.append([types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_events")])

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)


    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Начало отметки — запрос фото
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("attend_event:"))
async def cb_attend_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    try:
        idx = int(callback.data.split(":")[1])
    except:
        await callback.answer("❌ Ошибка выбора")
        return

    clear_user_state(user_states, uid)

    user_states[uid] = {
        "state": "waiting_event_photo",
        "event_index": idx,
        "ts": time.time(),
    }
    save(user_states, USER_STATES_PATH)

    await callback.message.edit_text(
        "📸 Отправьте фото с мероприятия (одно).", reply_markup=cancel_btn
    )
    await callback.answer()


# ---------------------------------------------------------------
# Приём фото от студента
# ---------------------------------------------------------------
@dp.message(
    lambda m: m.photo
    and user_states.get(str(m.from_user.id), {}).get("state") == "waiting_event_photo"
)
async def receive_event_photo(message: types.Message):
    uid = str(message.from_user.id)

    if not is_authenticated(uid):
        await message.answer(
            "❌ Сначала авторизуйтесь",
            reply_markup=build_user_menu(uid),
        )
        return

    st = user_states.get(uid, {})
    idx = st.get("event_index")

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    if idx is None or idx >= len(events):
        clear_user_state(user_states, uid)
        await message.answer("❌ Ошибка мероприятия", reply_markup=build_user_menu(uid))
        return

    ev = events[idx]
    event_name = ev.get("event_name", "")
    event_id = ev.get("template_id", idx)

    # Сохраняем фото
    ensure_photos_dir()
    photo = message.photo[-1]
    file_id = photo.file_id
    filename = f"{uid}_{int(time.time())}_event.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

    try:
        file_obj = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_obj.file_path}"

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

    # Создаём / загружаем файл заявок
    apps = load(APPLICATIONS_PATH) or {}
    apps.setdefault("applications", [])

    # Берём email из токенов по uid (телеграм-id)
    email = tokens.get(uid, {}).get("email")

    apps["applications"].append(
        {
            "id": int(time.time()),
            "user_id": uid,  # строковый telegram id
            "user_email": email,  # критично для баллов
            "event_id": event_id,
            "event_name": event_name,
            "timestamp": int(time.time()),
            "status": "pending",
            "event_photo_path": path,
            "event_photo_id": file_id,
        }
    )
    save(apps, APPLICATIONS_PATH)

    # Чистим состояние
    clear_user_state(user_states, uid)

    # Сообщение студенту
    await message.answer(
        f"✅ Вы успешно отметились на мероприятии:\n{event_name}",
        reply_markup=build_user_menu(uid),
    )


# ---------------------------------------------------------------
# «Мои заявки»
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_my_applications")
async def cb_my_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
            ]
        )
        await callback.message.edit_text("❌ Сначала авторизуйтесь", reply_markup=kb)
        await callback.answer()
        return

    apps = load(APPLICATIONS_PATH) or {}
    my_apps = [a for a in apps.get("applications", []) if str(a.get("user_id")) == str(uid)]

    if not my_apps:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.edit_text("📭 У вас пока нет заявок", reply_markup=kb)
        await callback.answer()
        return

    lines = []
    for i, app in enumerate(my_apps, start=1):
        status = app.get("status")
        event_name = app.get("event_name", "(без названия)")

        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "❓")
        text = {
            "pending": "На рассмотрении",
            "approved": "Одобрена",
            "rejected": "Отклонена",
        }.get(status, "Неизвестно")

        lines.append(f"{i}. {emoji} {event_name} — {text}")

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📊 Ваши заявки:\n\n" + "\n".join(lines), reply_markup=kb
    )
    await callback.answer()

# ================================================================
# bot_local.py — Часть 4/4
# Админ-функции: создание мероприятий, создание пользователей,
# удаление пользователей, рассмотрение заявок
# ================================================================


# ---------------------------------------------------------------
# Создание мероприятия — старт
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data == "btn_create_event")
async def cb_create_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    clear_user_state(user_states, uid)

    user_states[uid] = {"state": "admin_event_name", "ts": time.time()}
    save(user_states, USER_STATES_PATH)

    # ✅ ВАЖНО: сохраняем prompt, чтобы потом удалить
    msg = await callback.message.edit_text(
        "📝 Введите название мероприятия:", reply_markup=cancel_btn
    )

    user_states[uid]["prompt"] = msg.message_id
    save(user_states, USER_STATES_PATH)

    await callback.answer()


# ---------------------------------------------------------------
# Создание мероприятия — ввод названия
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "admin_event_name")
async def admin_event_name(message: types.Message):
    uid = str(message.from_user.id)
    name = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    if not name:
        err = await message.answer("❌ Название не может быть пустым")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = user_states[uid]

    # Удаляем предыдущий prompt
    await delete_prompts(uid, message.chat.id)

    st["name"] = name
    st["state"] = "admin_event_description"
    save(user_states, USER_STATES_PATH)

    msg = await message.answer("📝 Введите описание мероприятия:", reply_markup=cancel_btn)
    st.setdefault("prompts", []).append(msg.message_id)
    save(user_states, USER_STATES_PATH)
    save(user_states, USER_STATES_PATH)


# ---------------------------------------------------------------
# Создание мероприятия — описание
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "admin_event_description")
async def admin_event_description(message: types.Message):
    uid = str(message.from_user.id)
    desc = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = user_states[uid]

    # Удаляем предыдущий prompt
    await delete_prompts(uid, message.chat.id)

    st["description"] = desc
    st["state"] = "admin_event_profile"
    save(user_states, USER_STATES_PATH)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Профильное", callback_data="event_prof:yes")],
            [types.InlineKeyboardButton(text="❌ Непрофильное", callback_data="event_prof:no")],
            [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")],
        ]
    )

    msg = await message.answer("🎯 Мероприятие профильное?", reply_markup=kb)
    st.setdefault("prompts", []).append(msg.message_id)
    save(user_states, USER_STATES_PATH)
    save(user_states, USER_STATES_PATH)


# ---------------------------------------------------------------
# Создание мероприятия — выбор профильности
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("event_prof:"))
async def admin_event_profile(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})

    choice = callback.data.split(":")[1]
    st["is_profile"] = (choice == "yes")
    st["state"] = "admin_event_date"
    save(user_states, USER_STATES_PATH)

    msg = await callback.message.edit_text("📅 Укажите дату (ДД-ММ-ГГГГ):", reply_markup=cancel_btn)
    st.setdefault("prompts", []).append(msg.message_id)
    save(user_states, USER_STATES_PATH)

# ---------------------------------------------------------------
# Создание мероприятия — ввод даты
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "admin_event_date")
async def admin_event_date(message: types.Message):
    uid = str(message.from_user.id)
    date_text = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    # Проверка формата
    try:
        dt = time.strptime(date_text, "%d-%m-%Y")
        ts = int(time.mktime(dt))
    except:
        err = await message.answer("❌ Неверный формат. Пример: 31-12-2025")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = user_states[uid]

    await delete_prompts(uid, message.chat.id)

    events_raw = load(EVENTS_PATH) or {}
    events_raw.setdefault("events", [])

    event = {
        "template_id": int(time.time()),
        "event_name": st["name"],
        "description": st["description"],
        "is_profile": st["is_profile"],
        "event_date": date_text,
        "event_date_ts": ts,
        "is_template": True,
        "is_active": True,
        "created_by": uid,
        "timestamp": int(time.time()),
    }

    events_raw["events"].append(event)
    save(events_raw, EVENTS_PATH)

    clear_user_state(user_states, uid)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]]
    )

    await message.answer(
        f"✅ Мероприятие создано:\n{st['name']}\n📅 {date_text}", reply_markup=kb
    )


# ===============================================================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ (СТУДЕНТ / АДМИН)
# ===============================================================

@dp.callback_query(lambda c: c.data == "btn_admin_register")
async def cb_admin_register(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    clear_user_state(user_states, uid)

    user_states[uid] = {"state": "reg_email", "ts": time.time()}
    save(user_states, USER_STATES_PATH)

    await callback.message.edit_text("📧 Введите email нового пользователя:", reply_markup=cancel_btn)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_admin_students")
async def cb_admin_students(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    students = [info for info in user_info.values() if info.get("role") == "student"]

    if not students:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.edit_text("📭 Студентов нет", reply_markup=kb)
        await callback.answer()
        return

    user_states[uid] = {"state": "students_list", "students": students, "page": 0}
    save(user_states, USER_STATES_PATH)

    await show_students_page(callback.message, uid, 0)
    await callback.answer()


STUDENTS_PAGE_SIZE = 10

async def show_students_page(message: types.Message, admin_id: str, page: int):
    st = user_states.get(admin_id, {})
    students = st.get("students", [])

    total = len(students)
    max_page = (total - 1) // STUDENTS_PAGE_SIZE

    if page < 0:
        page = 0
    if page > max_page:
        page = max_page

    start = page * STUDENTS_PAGE_SIZE
    end = min(start + STUDENTS_PAGE_SIZE, total)
    chunk = students[start:end]

    # Заголовок
    text = "👥 Список студентов:\n"

    # Кнопки студентов
    buttons = []
    for s in chunk:
        name = f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
        email = s.get("email")

        buttons.append([
            types.InlineKeyboardButton(
                text=f"📄 {name}",
                callback_data=f"student_open:{email}"
            )
        ])

    # Навигация
    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="students_prev"))
    if page < max_page:
        nav_row.append(types.InlineKeyboardButton(text="Вперёд ➡️", callback_data="students_next"))

    if nav_row:
        buttons.append(nav_row)

    # Кнопка назад
    buttons.append([types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")])

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await message.edit_text(text, reply_markup=kb)
    except:
        await message.answer(text, reply_markup=kb)

    st["page"] = page
    user_states[admin_id] = st
    save(user_states, USER_STATES_PATH)


@dp.callback_query(lambda c: c.data == "students_prev")
async def students_prev(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})
    page = st.get("page", 0)
    await show_students_page(callback.message, uid, page - 1)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "students_next")
async def students_next(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})
    page = st.get("page", 0)
    await show_students_page(callback.message, uid, page + 1)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("student_open:"))
async def students_open(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    email = callback.data.split(":")[1]

    student = user_info.get(email)
    if not student:
        await callback.answer("❌ Студент не найден")
        return

    name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()

    text = (
        f"👤 Студент:\n"
        f"{name}\n"
        f"📧 {email}\n"
        f"🎓 Роль: студент\n"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"student_delete:{email}")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_admin_students")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Регистрация — email
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "reg_email")
async def reg_email(message: types.Message):
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

    st = user_states[uid]
    st["email"] = email
    st["state"] = "reg_firstname"
    save(user_states, USER_STATES_PATH)

    msg = await message.answer("👤 Введите имя:", reply_markup=cancel_btn)
    st.setdefault("prompts", []).append(msg.message_id)
    save(user_states, USER_STATES_PATH)
    save(user_states, USER_STATES_PATH)


# ---------------------------------------------------------------
# Регистрация — имя
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "reg_firstname")
async def reg_firstname(message: types.Message):
    uid = str(message.from_user.id)
    firstname = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = user_states[uid]
    st["firstname"] = firstname
    st["state"] = "reg_lastname"
    save(user_states, USER_STATES_PATH)

    msg = await message.answer("👤 Введите фамилию:", reply_markup=cancel_btn)
    st.setdefault("prompts", []).append(msg.message_id)
    save(user_states, USER_STATES_PATH)


# ---------------------------------------------------------------
# Регистрация — фамилия
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "reg_lastname")
async def reg_lastname(message: types.Message):
    uid = str(message.from_user.id)
    lastname = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = user_states[uid]
    st["lastname"] = lastname
    st["state"] = "reg_role"
    save(user_states, USER_STATES_PATH)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🎓 Студент", callback_data="reg_role:student")],
            [types.InlineKeyboardButton(text="👑 Администратор", callback_data="reg_role:admin")],
            [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")],
        ]
    )

    await message.answer("Выберите роль:", reply_markup=kb)


# ---------------------------------------------------------------
# Регистрация — выбор роли
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("reg_role:"))
async def reg_role(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    role = callback.data.split(":")[1]

    st = user_states[uid]
    st["role"] = role

    # Если админ — пропускаем фото
    if role == "admin":
        st["state"] = "reg_finish_admin"
        save(user_states, USER_STATES_PATH)

        await callback.message.edit_text("🔑 Введите пароль:", reply_markup=cancel_btn)
        await callback.answer()
        return

    # Если студент — продолжаем обычный поток
    st["state"] = "reg_password"
    save(user_states, USER_STATES_PATH)

    await callback.message.edit_text("🔑 Введите пароль:", reply_markup=cancel_btn)
    await callback.answer()


@dp.message(
    lambda m: user_states.get(str(m.from_user.id), {}).get("state")
    == "reg_finish_admin"
)
async def reg_finish_admin(message: types.Message):
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

    st = user_states[uid]
    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]

    # Создаём админа без фото
    user_info[email] = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password_hash": hash_password(pwd),
        "role": "admin",
        "student_photo_path": None,
        "student_photo_id": None,
    }
    save(user_info, USER_INFO_PATH)

    clear_user_state(user_states, uid)

    await message.answer(
        f"✅ Администратор создан:\n"
        f"{firstname} {lastname}\n"
        f"📧 {email}\n"
        f"👑 Роль: Администратор",
        reply_markup=build_admin_menu(uid),
    )


# ---------------------------------------------------------------
# Регистрация — пароль
# ---------------------------------------------------------------
@dp.message(lambda m: user_states.get(str(m.from_user.id), {}).get("state") == "reg_password")
async def reg_password(message: types.Message):
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

    st = user_states[uid]
    st["password"] = pwd
    st["state"] = "reg_photo"
    save(user_states, USER_STATES_PATH)

    await message.answer("📸 Отправьте фото пользователя:", reply_markup=cancel_btn)


# ---------------------------------------------------------------
# Регистрация — фото
# ---------------------------------------------------------------
@dp.message(lambda m: m.photo and user_states.get(str(m.from_user.id), {}).get("state") == "reg_photo")
async def reg_photo(message: types.Message):
    uid = str(message.from_user.id)
    st = user_states[uid]

    email = st["email"]
    firstname = st["firstname"]
    lastname = st["lastname"]
    role = st["role"]
    pwd = st["password"]

    # Сохраняю фото
    ensure_photos_dir()
    photo = message.photo[-1]
    file_id = photo.file_id
    filename = f"{email}_{int(time.time())}_base.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

    try:
        file_obj = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_obj.file_path}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                with open(path, "wb") as f:
                    f.write(resp.content)
            else:
                raise Exception()
    except:
        try:
            await photo.download(destination_file=path)
        except:
            await message.answer("❌ Не удалось сохранить фото")
            return

    # Создаю пользователя
    user_info[email] = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password_hash": hash_password(pwd),
        "role": role,
        "student_photo_path": path,
        "student_photo_id": file_id,
    }
    save(user_info, USER_INFO_PATH)

    clear_user_state(user_states, uid)

    await message.answer(
        f"✅ Пользователь создан:\n"
        f"{firstname} {lastname}\n"
        f"📧 {email}\n"
        f"👤 Роль: {'Администратор' if role == 'admin' else 'Студент'}",
        reply_markup=build_admin_menu(uid),
    )


# ===============================================================
# РАССМОТРЕНИЕ ЗАЯВОК
# ===============================================================


@dp.callback_query(lambda c: c.data == "btn_review_applications")
async def cb_review_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    apps = load(APPLICATIONS_PATH) or {}
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    if not pending:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.edit_text("📭 Нет заявок", reply_markup=kb)
        await callback.answer()
        return

    clear_user_state(user_states, uid)
    user_states[uid] = {"state": "review", "index": 0}
    save(user_states, USER_STATES_PATH)

    await show_application(callback.message, uid, 0)
    await callback.answer()


async def show_application(message: types.Message, admin_id: str, index: int):
    apps = load(APPLICATIONS_PATH) or {}
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    # Если заявок нет или индекс вышел за пределы
    if not pending or index >= len(pending):
        clear_user_state(user_states, admin_id)

        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )

        try:
            await message.edit_text("✅ Все заявки рассмотрены", reply_markup=kb)
        except:
            await message.answer("✅ Все заявки рассмотрены", reply_markup=kb)

        return

    app = pending[index]

    # Данные студента
    email = app.get("user_email")
    first = user_info.get(email, {}).get("first_name", "Неизвестно")
    last = user_info.get(email, {}).get("last_name", "")
    full_name = f"{first} {last}".strip()

    text = (
        f"🎯 Мероприятие: {app['event_name']}\n"
        f"👤 Участник: {full_name}\n"
        f"📧 Email: {email}\n\n"
        f"Заявка {index + 1} из {len(pending)}"
    )

    # Кнопки
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Принять", callback_data=f"app_accept:{app['id']}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"app_reject:{app['id']}"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ],
        ]
    )

    # Обновляем текст заявки (или создаём новое сообщение)
    try:
        msg_main = await message.edit_text(text)
    except:
        msg_main = await message.answer(text)

    chat_id = msg_main.chat.id

    # Фото студента
    base_photo = user_info.get(email, {}).get("student_photo_id")
    if base_photo:
        await bot.send_photo(chat_id, base_photo, caption="📎 Фото студента")

    # Фото с мероприятия
    event_photo = app.get("event_photo_id")
    if event_photo:
        await bot.send_photo(chat_id, event_photo, caption="📸 Фото с мероприятия")

    # Меню с кнопками (отдельным сообщением, чтобы потом его удалять)
    menu_msg = await message.answer("Выберите действие:", reply_markup=kb)

    # Сохраняем id меню, чтобы потом его убрать
    st = user_states.get(admin_id, {})
    st["menu_message_id"] = menu_msg.message_id
    st["index"] = index
    st["state"] = "review"
    user_states[admin_id] = st
    save(user_states, USER_STATES_PATH)

PAGE_SIZE = 10  # количество мероприятий на странице

async def show_admin_events_page(message: types.Message, admin_id: str, page: int):
    st = user_states.get(admin_id, {})
    events = st.get("events", [])
    flt = st.get("filter", "all")

    # применяем фильтр
    if flt == "active":
        events_filtered = [e for e in events if e.get("is_active", True)]
    elif flt == "inactive":
        events_filtered = [e for e in events if not e.get("is_active", True)]
    else:
        events_filtered = events

    if not events_filtered:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🟢 Активные", callback_data="flt_active"
                    ),
                    types.InlineKeyboardButton(
                        text="🔴 Завершённые", callback_data="flt_inactive"
                    ),
                    types.InlineKeyboardButton(text="📋 Все", callback_data="flt_all"),
                ],
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ],
            ]
        )
        try:
            await message.edit_text(
                "📭 Нет мероприятий по выбранному фильтру", reply_markup=kb
            )
        except:
            await message.answer(
                "📭 Нет мероприятий по выбранному фильтру", reply_markup=kb
            )
        return

    total = len(events_filtered)
    max_page = (total - 1) // PAGE_SIZE

    if page < 0:
        page = 0
    if page > max_page:
        page = max_page

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    chunk = events_filtered[start:end]

    lines = []
    for idx, ev in enumerate(chunk, start=start + 1):
        name = ev.get("event_name", "(без названия)")
        date = ev.get("event_date", "-")
        is_prof = ev.get("is_profile", False)
        is_active = ev.get("is_active", True)

        prof_text = "профильное" if is_prof else "непрофильное"

        # ✅ цветные индикаторы
        status_circle = "🟢" if is_active else "🔴"

        lines.append(f"{idx}. {status_circle} {name} — {date} ({prof_text})")

    text = "📋 Список мероприятий:\n\n" + "\n".join(lines)
    text += f"\n\nСтраница {page + 1} из {max_page + 1}"

    # кнопки фильтров
    filter_row = [
        types.InlineKeyboardButton(text="🟢 Активные", callback_data="flt_active"),
        types.InlineKeyboardButton(text="🔴 Завершённые", callback_data="flt_inactive"),
        types.InlineKeyboardButton(text="📋 Все", callback_data="flt_all"),
    ]

    # кнопки листания
    nav_row = []
    if page > 0:
        nav_row.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data="admin_events_prev"
            )
        )
    if page < max_page:
        nav_row.append(
            types.InlineKeyboardButton(
                text="Вперёд ➡️", callback_data="admin_events_next"
            )
        )

    buttons = [filter_row]
    if nav_row:
        buttons.append(nav_row)
    buttons.append(
        [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await message.edit_text(text, reply_markup=kb)
    except:
        await message.answer(text, reply_markup=kb)

    st["page"] = page
    user_states[admin_id] = st
    save(user_states, USER_STATES_PATH)


@dp.callback_query(lambda c: c.data == "flt_active")
async def flt_active(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})

    # ✅ если фильтр уже активен — ничего не делаем
    if st.get("filter") == "active":
        await callback.answer("Уже выбраны активные")
        return

    st["filter"] = "active"
    st["page"] = 0
    user_states[uid] = st
    save(user_states, USER_STATES_PATH)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "flt_inactive")
async def flt_inactive(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})

    # ✅ если фильтр уже активен — ничего не делаем
    if st.get("filter") == "inactive":
        await callback.answer("Уже выбраны завершённые")
        return

    st["filter"] = "inactive"
    st["page"] = 0
    user_states[uid] = st
    save(user_states, USER_STATES_PATH)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "flt_all")
async def flt_all(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})

    # ✅ если фильтр уже активен — ничего не делаем
    if st.get("filter") == "all":
        await callback.answer("Уже выбраны все")
        return

    st["filter"] = "all"
    st["page"] = 0
    user_states[uid] = st
    save(user_states, USER_STATES_PATH)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_events_prev")
async def cb_admin_events_prev(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    st = user_states.get(uid, {})
    if st.get("state") != "admin_events_list":
        await callback.answer()
        return

    current_page = st.get("page", 0)
    new_page = current_page - 1

    await show_admin_events_page(callback.message, uid, new_page)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_events_next")
async def cb_admin_events_next(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    st = user_states.get(uid, {})
    if st.get("state") != "admin_events_list":
        await callback.answer()
        return

    current_page = st.get("page", 0)
    new_page = current_page + 1

    await show_admin_events_page(callback.message, uid, new_page)
    await callback.answer()


# ---------------------------------------------------------------
# Принятие / отклонение заявки
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith(("app_accept:", "app_reject:")))
async def cb_process_application(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens.get(uid, {}).get("role") != "admin":
        await callback.answer("❌ Только администратор")
        return

    action, app_id_str = callback.data.split(":")
    app_id = int(app_id_str)

    apps = load(APPLICATIONS_PATH) or {}
    applications = apps.get("applications", [])

    app = next((a for a in applications if a["id"] == app_id), None)
    if not app:
        await callback.answer("❌ Заявка не найдена")
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])
    ev = next((e for e in events if e.get("template_id") == app["event_id"]), None)

    if action == "app_accept":
        app["status"] = "approved"

        # начисление баллов
        if ev:
            is_prof = ev.get("is_profile", False)
            base = 2
            mult = 1.5 if is_prof else 0.5
            points = int(base * mult)

            # 1) email из заявки
            email = app.get("user_email")
            # 2) если пусто — пробуем взять из токенов по user_id
            if not email:
                email = tokens.get(str(app["user_id"]), {}).get("email")

            # DEBUG
            print("=== BALANCE DEBUG ===")
            print("APP ID:", app["id"])
            print("APP USER_ID:", repr(app["user_id"]))
            print("APP EMAIL:", repr(app.get("user_email")))
            print("RESOLVED EMAIL:", repr(email))
            print("TOKENS:", tokens)
            print("=====================")

            if email:
                # ищем токен по email
                student_key = next(
                    (k for k, v in tokens.items() if v.get("email") == email),
                    None,
                )

                if student_key:
                    tokens[student_key]["practice_points"] = (
                        tokens[student_key].get("practice_points", 0) + points
                    )
                else:
                    # создаём новый токен по email
                    tokens[email] = {
                        "email": email,
                        "token": None,
                        "role": "student",
                        "practice_points": points,
                    }

                save(tokens, USER_TOKENS_PATH)

        # Сообщение студенту
        try:
            await bot.send_message(
                app["user_id"],
                f"✅ Ваша заявка на мероприятие '{app['event_name']}' одобрена!",
            )
        except Exception:
            pass

        admin_result_text = (
            f"✅ Вы подтвердили участие студента в мероприятии:\n{app['event_name']}"
        )

    else:
        app["status"] = "rejected"

        try:
            await bot.send_message(
                app["user_id"],
                f"❌ Ваша заявка на мероприятие '{app['event_name']}' отклонена.",
            )
        except Exception:
            pass

        admin_result_text = (
            f"❌ Вы отклонили участие студента в мероприятии:\n{app['event_name']}"
        )

    save(apps, APPLICATIONS_PATH)

    st = user_states.get(uid, {})
    menu_id = st.get("menu_message_id")
    if menu_id:
        await delete_message_safe(callback.message.chat.id, menu_id)
        st["menu_message_id"] = None

    await callback.message.answer(admin_result_text)

    apps = load(APPLICATIONS_PATH) or {}
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    if not pending:
        clear_user_state(user_states, uid)
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.answer("✅ Все заявки рассмотрены", reply_markup=kb)
        await callback.answer()
        return

    current_index = st.get("index", 0)
    user_states[uid] = {"state": "review", "index": current_index}
    save(user_states, USER_STATES_PATH)

    await show_application(callback.message, uid, current_index)
    await callback.answer()


# ===============================================================
# Список мероприятий
# ===============================================================


@dp.callback_query(lambda c: c.data == "btn_list_events")
async def cb_list_events(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens.get(uid, {}).get("role") != "admin":
        await callback.answer("❌ Только администратор")
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    if not events:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="◀️ В меню", callback_data="btn_back_to_menu"
                    )
                ]
            ]
        )
        await callback.message.edit_text("📭 Мероприятий нет", reply_markup=kb)
        return

    # сортировка по дате (новые → старые)
    events_sorted = sorted(
        events, key=lambda e: e.get("event_date_ts", 0), reverse=True
    )

    user_states[uid] = {
        "state": "admin_events_list",
        "events": events_sorted,
        "page": 0,
        "filter": "all",  # all | active | inactive
    }
    save(user_states, USER_STATES_PATH)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


# ===============================================================
# Показ мероприятий админа
# ===============================================================
async def show_admin_event(message: types.Message, admin_id: str, index: int):
    st = user_states.get(admin_id, {})
    events = st.get("events", [])

    if not events:
        await message.answer("📭 Нет мероприятий")
        return

    if index < 0:
        index = 0
    if index >= len(events):
        index = len(events) - 1

    ev = events[index]

    text = (
        f"📌 {ev.get('event_name')}\n"
        f"📅 Дата: {ev.get('event_date')}\n"
        f"📝 {ev.get('description')}\n"
        f"🎯 {'Профильное' if ev.get('is_profile') else 'Непрофильное'}\n\n"
        f"Мероприятие {index + 1} из {len(events)}"
    )

    # кнопки листания
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="⬅️", callback_data="admin_event_prev"),
                types.InlineKeyboardButton(text="➡️", callback_data="admin_event_next"),
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ],
        ]
    )

    try:
        await message.edit_text(text, reply_markup=kb)
    except:
        await message.answer(text, reply_markup=kb)

    # сохраняем индекс
    st["index"] = index
    user_states[admin_id] = st
    save(user_states, USER_STATES_PATH)

@dp.callback_query(lambda c: c.data == "admin_event_prev")
async def admin_event_prev(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})
    idx = st.get("index", 0) - 1
    await show_admin_event(callback.message, uid, idx)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_event_next")
async def admin_event_next(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = user_states.get(uid, {})
    idx = st.get("index", 0) + 1
    await show_admin_event(callback.message, uid, idx)
    await callback.answer()


# ===============================================================
# Завершение мероприятия
# ===============================================================
@dp.callback_query(lambda c: c.data == "btn_finish_event")
async def cb_finish_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    # выбираем только активные мероприятия
    active = [e for e in events if e.get("is_template") and e.get("is_active", True)]
    if not active:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
            ]
        )
        await callback.message.edit_text("📭 Нет активных мероприятий", reply_markup=kb)
        await callback.answer()
        return

    # формируем список кнопок
    rows = []
    for idx, ev in enumerate(events):
        if ev.get("is_template") and ev.get("is_active", True):
            name = ev.get("event_name", "(без названия)")
            date = ev.get("event_date", "-")
            rows.append([
                types.InlineKeyboardButton(
                    text=f"{name} — {date}",
                    callback_data=f"finish_event:{idx}"
                )
            ])

    rows.append([types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")])

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("🏁 Выберите мероприятие для завершения:", reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Подтверждение завершения мероприятия
# ---------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("finish_event:"))
async def cb_finish_event_confirm(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if not is_authenticated(uid) or tokens[uid]["role"] != "admin":
        await callback.answer("❌ Только администратор")
        return

    try:
        idx = int(callback.data.split(":")[1])
    except:
        await callback.answer("❌ Ошибка выбора")
        return

    events_raw = load(EVENTS_PATH) or {}
    events = events_raw.get("events", [])

    if idx < 0 or idx >= len(events):
        await callback.answer("❌ Мероприятие не найдено")
        return

    # помечаем как завершённое
    events[idx]["is_active"] = False
    save({"events": events}, EVENTS_PATH)

    name = events[idx].get("event_name", "(без названия)")

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
        ]
    )

    await callback.message.edit_text(f"✅ Мероприятие «{name}» завершено", reply_markup=kb)
    await callback.answer()


# ===============================================================
# Удаление пользователя администратором
# ===============================================================
@dp.callback_query(lambda c: c.data.startswith("student_delete:"))
async def student_delete(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    email = callback.data.split(":")[1]

    # Удаляем из user_info
    user_info.pop(email, None)
    save(user_info, USER_INFO_PATH)

    # Удаляем токены по email
    to_delete = [k for k, v in tokens.items() if v.get("email") == email]
    for k in to_delete:
        tokens.pop(k, None)
    save(tokens, USER_TOKENS_PATH)

    # Удаляем заявки
    apps = load(APPLICATIONS_PATH) or {}
    apps["applications"] = [
        a for a in apps.get("applications", []) if a.get("user_email") != email
    ]
    save(apps, APPLICATIONS_PATH)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ]
        ]
    )

    await callback.message.edit_text(f"✅ Студент {email} удалён", reply_markup=kb)
    await callback.answer()


# ===============================================================
# Запуск бота
# ===============================================================
async def work():
    """Точка входа — запуск polling."""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(work())
