# handlers/student.py
"""
Студент: список мероприятий, карточка, отметка, мои заявки.
Новый стиль: единый FSM, чистые сообщения, исчезающие ошибки.
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

from services.bot.local_bot.fsm import fsm
from services.bot.local_bot.keyboards import (
    back_to_menu_kb,
    build_user_menu,
)
from services.bot.local_bot.utils import (
    ensure_photos_dir,
    delete_message_safe,
)
from services.bot.local_bot.config import PHOTOS_DIR

student_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_authenticated(uid: str) -> bool:
    u = tokens.get(uid)
    return bool(u and u.get("token"))


def _sort_events(events):
    return sorted(events, key=lambda e: e.get("event_date_ts", 0))


# ================================================================
# СПИСОК МЕРОПРИЯТИЙ
# ================================================================
@student_router.callback_query(lambda c: c.data == "btn_events")
async def cb_events(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_authenticated(uid):
        await fsm(uid).show_menu(
            callback.bot, chat_id, "❌ Сначала авторизуйтесь", back_to_menu_kb()
        )
        await callback.answer()
        return

    events_raw = load_events()
    events = _sort_events(events_raw.get("events", []))

    active = [ev for ev in events if ev.get("is_template") and ev.get("is_active")]

    if not active:
        await fsm(uid).show_menu(
            callback.bot, chat_id, "📭 Нет активных мероприятий", back_to_menu_kb()
        )
        await callback.answer()
        return

    rows = []
    for ev in active:
        name = ev["event_name"]
        date = ev["event_date"]
        tid = ev["template_id"]
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{name} — {date}", callback_data=f"view_event:{tid}"
                )
            ]
        )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ],
        ]
    )

    await callback.message.edit_text("📅 Активные мероприятия:", reply_markup=kb)
    await callback.answer()


# ================================================================
# КАРТОЧКА МЕРОПРИЯТИЯ
# ================================================================
@student_router.callback_query(lambda c: c.data.startswith("view_event:"))
async def cb_view_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    tid = int(callback.data.split(":")[1])

    events_raw = load_events()
    events = events_raw.get("events", [])

    ev = next((e for e in events if e["template_id"] == tid), None)
    if not ev:
        await callback.answer("❌ Мероприятие не найдено")
        return

    name = ev["event_name"]
    date = ev["event_date"]
    desc = ev["description"]
    is_prof = ev["is_profile"]

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

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📸 Отметиться", callback_data=f"attend_event:{tid}"
                )
            ],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="btn_events")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ================================================================
# НАЧАЛО ОТМЕТКИ
# ================================================================
@student_router.callback_query(lambda c: c.data.startswith("attend_event:"))
async def cb_attend_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_authenticated(uid):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    tid = int(callback.data.split(":")[1])

    f = fsm(uid)
    f.clear()
    f.set(state="waiting_event_photo", event_tid=tid)

    msg = await callback.message.edit_text("📸 Отправьте фото с мероприятия (одно).")
    f.add_prompt(msg.message_id)

    await callback.answer()


# ================================================================
# ПРИЁМ ФОТО
# ================================================================
@student_router.message(
    lambda m: m.photo
    and fsm(str(m.from_user.id)).get().get("state") == "waiting_event_photo"
)
async def receive_event_photo(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)
    st = f.get()

    if not is_authenticated(uid):
        await f.show_menu(
            message.bot, chat_id, "❌ Сначала авторизуйтесь", build_user_menu()
        )
        return

    tid = st.get("event_tid")

    # Удаляем инструкцию
    await f.clear_prompts(message.bot, chat_id)

    events_raw = load_events()
    events = events_raw.get("events", [])

    ev = next((e for e in events if e["template_id"] == tid), None)
    if not ev:
        f.clear()
        await f.show_menu(
            message.bot, chat_id, "❌ Ошибка мероприятия", build_user_menu()
        )
        return

    event_name = ev["event_name"]

    ensure_photos_dir()
    photo = message.photo[-1]
    file_id = photo.file_id
    filename = f"{uid}_{int(time.time())}_event.jpg"
    path = os.path.join(PHOTOS_DIR, filename)

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

    # Создаём заявку
    apps = load_applications()
    apps.setdefault("applications", [])

    email = tokens.get(uid, {}).get("email")

    apps["applications"].append(
        {
            "id": int(time.time()),
            "user_id": uid,
            "user_email": email,
            "event_id": tid,
            "event_name": event_name,
            "timestamp": int(time.time()),
            "status": "pending",
            "event_photo_path": path,
            "event_photo_id": file_id,
        }
    )
    save_applications(apps)

    f.clear()

    await f.show_menu(
        message.bot,
        chat_id,
        f"✅ Вы успешно отметились на мероприятии:\n{event_name}",
        build_user_menu(),
    )


# ================================================================
# МОИ ЗАЯВКИ
# ================================================================
@student_router.callback_query(lambda c: c.data == "btn_my_applications")
async def cb_my_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_authenticated(uid):
        await fsm(uid).show_menu(
            callback.bot, chat_id, "❌ Сначала авторизуйтесь", back_to_menu_kb()
        )
        await callback.answer()
        return

    apps = load_applications()
    my_apps = [a for a in apps.get("applications", []) if str(a.get("user_id")) == uid]

    if not my_apps:
        await fsm(uid).show_menu(
            callback.bot, chat_id, "📭 У вас пока нет заявок", back_to_menu_kb()
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
