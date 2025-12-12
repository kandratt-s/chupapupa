# handlers/student.py
"""
Обработчики действий студента:
- список мероприятий
- просмотр мероприятия
- отметка (фото)
- мои заявки
"""

import time
import asyncio
import os
import httpx
from aiogram import Router, types

from services.bot.local_bot.storage import (
    tokens,
    load_events,
    save_events,
    load_applications,
    save_applications,
)

from services.bot.local_bot.fsm import (
    get_state,
    set_state,
    clear_state,
)

from services.bot.local_bot.keyboards import (
    back_to_menu_kb,
    build_user_menu,
)

from services.bot.local_bot.utils import (
    ensure_photos_dir,
    delete_message_safe,
)


student_router = Router()


def is_authenticated(uid: str) -> bool:
    """Проверка наличия активного токена."""
    u = tokens.get(uid)
    return bool(u and u.get("token"))


# ---------------------------------------------------------------
# Список мероприятий
# ---------------------------------------------------------------
@student_router.callback_query(lambda c: c.data == "btn_events")
async def cb_events(callback: types.CallbackQuery):
    """Показать студенту список активных мероприятий."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.message.edit_text(
            "❌ Сначала авторизуйтесь", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    events_raw = load_events()
    events = events_raw.get("events", [])

    active = [
        ev for ev in events if ev.get("is_template") and ev.get("is_active", True)
    ]

    if not active:
        await callback.message.edit_text(
            "📭 Нет активных мероприятий", reply_markup=back_to_menu_kb()
        )
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
# Просмотр мероприятия
# ---------------------------------------------------------------
@student_router.callback_query(lambda c: c.data.startswith("view_event:"))
async def cb_view_event(callback: types.CallbackQuery):
    """Показать подробности выбранного мероприятия."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    try:
        idx = int(callback.data.split(":")[1])
    except ValueError:
        await callback.answer("❌ Ошибка выбора")
        return

    events_raw = load_events()
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

    buttons = [
        [
            types.InlineKeyboardButton(
                text="✅ Отметиться", callback_data=f"attend_event:{idx}"
            )
        ],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_events")],
    ]

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------
# Начало отметки
# ---------------------------------------------------------------
@student_router.callback_query(lambda c: c.data.startswith("attend_event:"))
async def cb_attend_event(callback: types.CallbackQuery):
    """Студент нажал «Отметиться» — ждём фото."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    try:
        idx = int(callback.data.split(":")[1])
    except ValueError:
        await callback.answer("❌ Ошибка выбора")
        return

    set_state(
        uid,
        {
            "state": "waiting_event_photo",
            "event_index": idx,
            "ts": time.time(),
        },
    )

    await callback.message.edit_text("📸 Отправьте фото с мероприятия (одно).")
    await callback.answer()


# ---------------------------------------------------------------
# Приём фото
# ---------------------------------------------------------------
@student_router.message(
    lambda m: m.photo
    and get_state(str(m.from_user.id)).get("state") == "waiting_event_photo"
)
async def receive_event_photo(message: types.Message):
    """Обработка фото от студента."""
    uid = str(message.from_user.id)

    if not is_authenticated(uid):
        await message.answer("❌ Сначала авторизуйтесь", reply_markup=build_user_menu())
        return

    st = get_state(uid)
    idx = st.get("event_index")

    events_raw = load_events()
    events = events_raw.get("events", [])

    if idx is None or idx >= len(events):
        clear_state(uid)
        await message.answer("❌ Ошибка мероприятия", reply_markup=build_user_menu())
        return

    ev = events[idx]
    event_name = ev.get("event_name", "")
    event_id = ev.get("template_id", idx)

    # Сохранение фото
    ensure_photos_dir()
    photo = message.photo[-1]
    file_id = photo.file_id
    filename = f"{uid}_{int(time.time())}_event.jpg"
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

    # Создание заявки
    apps = load_applications()
    apps.setdefault("applications", [])

    email = tokens.get(uid, {}).get("email")

    apps["applications"].append(
        {
            "id": int(time.time()),
            "user_id": uid,
            "user_email": email,
            "event_id": event_id,
            "event_name": event_name,
            "timestamp": int(time.time()),
            "status": "pending",
            "event_photo_path": path,
            "event_photo_id": file_id,
        }
    )
    save_applications(apps)

    clear_state(uid)

    await message.answer(
        f"✅ Вы успешно отметились на мероприятии:\n{event_name}",
        reply_markup=build_user_menu(),
    )


# ---------------------------------------------------------------
# Мои заявки
# ---------------------------------------------------------------
@student_router.callback_query(lambda c: c.data == "btn_my_applications")
async def cb_my_applications(callback: types.CallbackQuery):
    """Показать студенту список его заявок."""
    uid = str(callback.from_user.id)

    if not is_authenticated(uid):
        await callback.message.edit_text(
            "❌ Сначала авторизуйтесь", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    apps = load_applications()
    my_apps = [a for a in apps.get("applications", []) if str(a.get("user_id")) == uid]

    if not my_apps:
        await callback.message.edit_text(
            "📭 У вас пока нет заявок", reply_markup=back_to_menu_kb()
        )
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

    await callback.message.edit_text(
        "📊 Ваши заявки:\n\n" + "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
