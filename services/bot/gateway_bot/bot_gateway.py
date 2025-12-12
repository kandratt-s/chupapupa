# bot_gateway.py
import asyncio
import time
import os
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from services.bot.local_bot.config import BOT_TOKEN, GATEWAY_URL
from services.bot.Bot_local.core.utils import validate_mail, validate_password, ensure_photos_dir

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Локальные сессии: tg_id -> {...}
sessions: dict[str, dict] = {}
user_states: dict[str, dict] = {}

cancel_btn = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")]
    ]
)


def is_authenticated(user_id: str) -> bool:
    sess = sessions.get(user_id)
    return bool(sess and sess.get("access_token"))


def build_user_menu(user_id: str):
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


def build_admin_menu(user_id: str):
    # pending можно получить из сервиса, но для упрощения здесь показываем без счётчика
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
                    text="📥 Рассмотреть заявки",
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
                    text="👤 Профиль", callback_data="btn_profile"
                )
            ],
            [types.InlineKeyboardButton(text="🚪 Выйти", callback_data="btn_logout")],
        ]
    )


def clear_user_state(user_id: str):
    user_states.pop(user_id, None)


def get_headers(uid: str) -> dict:
    sess = sessions.get(uid) or {}
    token = sess.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


@dp.message(Command("start"))
async def start_command(message: types.Message):
    uid = str(message.from_user.id)
    sess = sessions.get(uid)
    if sess and sess.get("role") == "admin" and sess.get("access_token"):
        await message.answer(
            f"👋 {sess.get('name', 'Админ')}, вы авторизованы как админ",
            reply_markup=build_admin_menu(uid),
        )
        return
    if sess and sess.get("role") == "student" and sess.get("access_token"):
        await message.answer(
            f"👋 {sess.get('name', 'Студент')}, вы авторизованы как студент",
            reply_markup=build_user_menu(uid),
        )
        return

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
        ]
    )
    await message.answer(
        "👋 Привет! Я бот для учёта посещаемости.\n\n"
        "Для входа используйте свой email и пароль.",
        reply_markup=kb,
    )


@dp.callback_query(lambda c: c.data == "btn_login")
async def cb_btn_login(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    clear_user_state(uid)
    user_states[uid] = {"state": "waiting_email", "ts": time.time()}
    msg = await callback.message.edit_text(
        "📧 Введите ваш email:", reply_markup=cancel_btn
    )
    user_states[uid]["prompt_message_id"] = msg.message_id
    await callback.answer()


@dp.message(
    lambda m: user_states.get(str(m.from_user.id), {}).get("state")
    in ("waiting_email", "waiting_password")
)
async def login_flow(message: types.Message):
    uid = str(message.from_user.id)
    st = user_states.get(uid, {})
    state = st.get("state")

    if state == "waiting_email":
        email = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if not validate_mail(email):
            await message.answer("❌ Некорректный email. Попробуйте снова.")
            return

        st["email"] = email
        st["state"] = "waiting_password"

        prev_mid = st.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        msg = await message.answer("🔑 Введите ваш пароль:", reply_markup=cancel_btn)
        st["prompt_message_id"] = msg.message_id
        user_states[uid] = st
        return

    if state == "waiting_password":
        password = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        prev_mid = st.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass

        email = st.get("email")
        if not email:
            clear_user_state(uid)
            await message.answer("❌ Ошибка: email не указан. Начните вход заново.")
            return

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{GATEWAY_URL}/auth/login",
                    json={"email": email, "password": password},
                    timeout=5.0,
                )
            except httpx.RequestError:
                await message.answer("❌ Ошибка соединения с сервером авторизации.")
                return

        if resp.status_code != 200:
            await message.answer("❌ Неверный email или пароль.")
            return

        data = resp.json()
        access_token = data.get("access_token")
        role = data.get("role", "student")
        name = data.get("first_name") or data.get("full_name") or "Пользователь"

        sessions[uid] = {
            "email": email,
            "access_token": access_token,
            "role": role,
            "name": name,
        }
        clear_user_state(uid)

        if role == "admin":
            await message.answer(
                f"✅ {name}, авторизация успешна!\n📧 Email: {email}\n👑 Роль: администратор",
                reply_markup=build_admin_menu(uid),
            )
        else:
            await message.answer(
                f"✅ {name}, авторизация успешна!\n📧 Email: {email}\n🎓 Роль: студент",
                reply_markup=build_user_menu(uid),
            )


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

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/users/profile",
            headers=get_headers(uid),
            timeout=5.0,
        )

    if resp.status_code != 200:
        await callback.message.edit_text("❌ Ошибка получения профиля")
        await callback.answer()
        return

    profile = resp.json()
    email = profile.get("email", "-")
    role = profile.get("role", "student")
    points = profile.get("practice_points", 0)

    if role == "admin":
        text = f"👤 Профиль:\n\n📧 Email: {email}\n👑 Роль: Администратор"
        kb = build_admin_menu(uid)
    else:
        text = f"👤 Профиль:\n\n📧 Email: {email}\n🎓 Роль: Студент\n⭐ Баллы практики: {points}"
        kb = build_user_menu(uid)

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_events")
async def cb_events(callback: types.CallbackQuery):
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

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/events/list",
            headers=get_headers(uid),
            timeout=5.0,
        )

    if resp.status_code != 200:
        await callback.message.edit_text("❌ Ошибка загрузки мероприятий")
        await callback.answer()
        return

    events = resp.json() or []
    active = [e for e in events if e.get("is_active")]

    if not active:
        await callback.message.edit_text(
            "📭 Нет активных мероприятий", reply_markup=build_user_menu(uid)
        )
        await callback.answer()
        return

    rows = []
    for ev in active:
        ev_id = ev.get("id")
        name = ev.get("event_name") or "(без названия)"
        date = ev.get("event_date") or "-"
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{name} — {date}",
                    callback_data=f"view_event:{ev_id}",
                )
            ]
        )

    rows.append(
        [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("📅 Активные мероприятия:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("view_event:"))
async def cb_view_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    ev_id = callback.data.split(":", 1)[1]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/events/{ev_id}",
            headers=get_headers(uid),
            timeout=5.0,
        )

    if resp.status_code != 200:
        await callback.message.edit_text(
            "❌ Мероприятие не найдено", reply_markup=build_user_menu(uid)
        )
        await callback.answer()
        return

    ev = resp.json()
    name = ev.get("event_name") or "(без названия)"
    date = ev.get("event_date") or "-"
    description = ev.get("description") or "Нет описания"
    is_profile = ev.get("is_profile", False)
    points_type = "профильное" if is_profile else "непрофильное"
    base_points = 2
    multiplier = 1.5 if is_profile else 0.5
    points = int(base_points * multiplier)

    text = (
        f"📌 {name}\n\n"
        f"📅 Дата: {date}\n"
        f"📝 Описание: {description}\n"
        f"🎯 Тип: {points_type}\n"
        f"⭐ Баллы: {points}"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Отметиться", callback_data=f"attend_event:{ev_id}"
                )
            ],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_events")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("attend_event:"))
async def cb_attend_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    ev_id = callback.data.split(":", 1)[1]
    clear_user_state(uid)
    user_states[uid] = {
        "state": "waiting_event_photo",
        "event_id": ev_id,
        "ts": time.time(),
    }

    await callback.message.edit_text(
        "📸 Отправьте одно фото с мероприятия (селфи/на фоне):",
        reply_markup=cancel_btn,
    )
    await callback.answer()


@dp.message(
    lambda m: m.photo
    and user_states.get(str(m.from_user.id), {}).get("state") == "waiting_event_photo"
)
async def send_event_photo(message: types.Message):
    uid = str(message.from_user.id)
    if not is_authenticated(uid):
        await message.answer(
            "❌ Сначала авторизуйтесь", reply_markup=build_user_menu(uid)
        )
        return

    st = user_states.get(uid, {})
    ev_id = st.get("event_id")
    if not ev_id:
        await message.answer("❌ Ошибка: мероприятие не выбрано")
        return

    photo = message.photo[-1]
    file_id = photo.file_id

    # В идеале: отправка файла сразу на файловый сервис.
    # Минимальная реализация: скачать фото, отправить как бинарь через gateway.
    ensure_photos_dir()
    filename = f"{uid}_{int(time.time())}_event.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

    try:
        file_obj = await bot.get_file(file_id)
        file_path = file_obj.file_path
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(file_url)
            if resp.status_code == 200:
                with open(path, "wb") as f:
                    f.write(resp.content)
            else:
                await message.answer("❌ Не удалось скачать файл")
                return
    except Exception:
        try:
            await photo.download(destination_file=path)
        except Exception:
            await message.answer("❌ Ошибка при сохранении фото")
            return

    async with httpx.AsyncClient() as client:
        with open(path, "rb") as f:
            files = {"file": ("event_photo.jpg", f, "image/jpeg")}
            data = {"event_id": ev_id}
            resp = await client.post(
                f"{GATEWAY_URL}/events/attend",
                headers=get_headers(uid),
                data=data,
                files=files,
                timeout=10.0,
            )

    os.remove(path) if os.path.exists(path) else None
    clear_user_state(uid)

    if resp.status_code != 200:
        await message.answer("❌ Не удалось отправить заявку")
        return

    await message.answer(
        "✅ Заявка отправлена! Ожидайте рассмотрения.",
        reply_markup=build_user_menu(uid),
    )


@dp.callback_query(lambda c: c.data == "btn_logout")
async def cb_logout(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    sessions.pop(uid, None)
    clear_user_state(uid)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
        ]
    )
    await callback.message.edit_text("👋 Вы вышли из аккаунта.", reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_cancel")
async def cb_cancel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    clear_user_state(uid)

    if is_authenticated(uid):
        role = sessions.get(uid, {}).get("role", "student")
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


# Остальные админские функции (создание событий, регистрация студентов, просмотр заявок)
# по аналогии надо будет реализовать через POST/GET на:
# - /events/create
# - /users/register
# - /events/applications
# - /events/applications/{id}/approve и т.п.
# Здесь я дал тебе основу для логики авторизации, просмотра профиля, списка мероприятий и отправки заявки.


async def work():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(work())
