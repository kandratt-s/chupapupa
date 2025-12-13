"""
Админ: создание мероприятий, список, карточка, завершение, удаление.
Новый стиль: единый FSM, карточки, чистые сообщения, исчезающие ошибки.
"""

import time
import asyncio
from aiogram import Router, types

from services.bot.local_bot.storage import (
    tokens,
    load_events,
    save_events,
)
from services.bot.local_bot.fsm import fsm
from services.bot.local_bot.keyboards import (
    cancel_kb,
    back_to_menu_kb,
    build_admin_menu,
)
from services.bot.local_bot.utils import (
    delete_message_safe,
)

# 🔥 Глобальный фильтр — блокирует команды внутри FSM
from services.bot.local_bot.filters import NotCommand

admin_events_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_admin(uid: str) -> bool:
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


def _sort_events(events):
    """Сортировка по дате."""
    return sorted(events, key=lambda e: e.get("event_date_ts", 0))


# ================================================================
# СОЗДАНИЕ МЕРОПРИЯТИЯ
# ================================================================
@admin_events_router.callback_query(lambda c: c.data == "btn_create_event")
async def cb_create_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    f = fsm(uid)
    f.clear()
    f.set(state="event_name")

    # Удаляем старое меню (текущее сообщение с кнопками)
    try:
        await callback.message.delete()
    except:
        pass

    msg = await callback.bot.send_message(
        chat_id, "📝 Введите название мероприятия:", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)

    await callback.answer()


# ---------------- NAME ----------------
@admin_events_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "event_name"
)
async def event_name(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    # Защита от ложного вызова
    st = f.get()
    if st.get("state") != "event_name":
        return

    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    name = message.text.strip()
    if not name:
        err = await message.answer("❌ Название не может быть пустым")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    f.set(name=name, state="event_description")
    await f.clear_prompts(message.bot, chat_id)

    msg = await message.answer("📝 Введите описание:", reply_markup=cancel_kb())
    f.add_prompt(msg.message_id)


# ---------------- DESCRIPTION ----------------
@admin_events_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "event_description"
)
async def event_description(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    # Защита от ложного вызова
    st = f.get()
    if st.get("state") != "event_description":
        return

    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    desc = message.text.strip()
    f.set(description=desc, state="event_profile")
    await f.clear_prompts(message.bot, chat_id)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🎯 Профильное", callback_data="event_prof:yes"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📘 Непрофильное", callback_data="event_prof:no"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отменить", callback_data="btn_cancel"
                )
            ],
        ]
    )

    msg = await message.answer("🎯 Мероприятие профильное?", reply_markup=kb)
    f.add_prompt(msg.message_id)


# ---------------- PROFILE ----------------
@admin_events_router.callback_query(lambda c: c.data.startswith("event_prof:"))
async def event_profile(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)

    # Защита от ложного вызова
    st = f.get()
    if st.get("state") != "event_profile":
        await callback.answer()
        return

    is_prof = callback.data.split(":")[1] == "yes"
    f.set(is_profile=is_prof, state="event_date")

    # Удаляем сообщение с выбором профильности
    await f.clear_prompts(callback.bot, chat_id)

    msg = await callback.bot.send_message(
        chat_id, "📅 Укажите дату (ДД-ММ-ГГГГ):", reply_markup=cancel_kb()
    )
    f.add_prompt(msg.message_id)

    await callback.answer()


# ---------------- DATE ----------------
@admin_events_router.message(
    lambda m: fsm(str(m.from_user.id)).get().get("state") == "event_date"
)
async def event_date(message: types.Message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    f = fsm(uid)

    st = f.get()
    if st.get("state") != "event_date":
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        await message.delete()
    except:
        pass

    date_text = message.text.strip()

    try:
        dt = time.strptime(date_text, "%d-%m-%Y")
        ts = int(time.mktime(dt))
    except:
        err = await message.answer("❌ Неверный формат. Пример: 31-12-2025")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id, message.bot)
        return

    name = st.get("name")
    description = st.get("description")
    is_profile = st.get("is_profile")

    events_raw = load_events()
    events_raw.setdefault("events", [])

    event = {
        "template_id": int(time.time()),
        "event_name": name,
        "description": description,
        "is_profile": is_profile,
        "event_date": date_text,
        "event_date_ts": ts,
        "is_template": True,
        "is_active": True,
        "created_by": uid,
        "timestamp": int(time.time()),
    }

    events_raw["events"].append(event)
    save_events(events_raw)

    await f.clear_prompts(message.bot, chat_id)
    f.clear()

    # ЛОГ (остаётся в чате)
    await f.log(
        message.bot, chat_id, f"✅ Мероприятие создано:\n{name}\n📅 {date_text}"
    )

    # МЕНЮ (отдельно)
    await f.show_menu(message.bot, chat_id, "👑 Админ‑панель", build_admin_menu())


# ================================================================
# СПИСОК МЕРОПРИЯТИЙ
# ================================================================
@admin_events_router.callback_query(lambda c: c.data == "btn_list_events")
async def cb_list_events(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    f = fsm(uid)
    f.clear()
    f.set(filter="active", page=0)

    await show_events(callback.message, uid)
    await callback.answer()


async def show_events(message: types.Message, uid: str):
    f = fsm(uid)
    st = f.get()

    filter_mode = st.get("filter", "active")
    page = st.get("page", 0)

    events_raw = load_events()
    events = _sort_events(events_raw.get("events", []))

    # Фильтры
    if filter_mode == "active":
        events = [e for e in events if e.get("is_active")]
    elif filter_mode == "finished":
        events = [e for e in events if not e.get("is_active")]

    if not events:
        await message.edit_text("📭 Нет мероприятий", reply_markup=back_to_menu_kb())
        return

    # Пагинация
    per_page = 6
    total_pages = (len(events) - 1) // per_page + 1
    page = max(0, min(page, total_pages - 1))

    f.set(page=page)

    start = page * per_page
    chunk = events[start : start + per_page]

    rows = []
    for ev in chunk:
        name = ev["event_name"]
        date = ev["event_date"]
        tid = ev["template_id"]
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{name} — {date}", callback_data=f"event_card:{tid}"
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️", callback_data="events_prev"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton(text="➡️", callback_data="events_next"))

    filter_row = [
        types.InlineKeyboardButton(text="🔵 Все", callback_data="events_filter:all"),
        types.InlineKeyboardButton(
            text="🟢 Активные", callback_data="events_filter:active"
        ),
        types.InlineKeyboardButton(
            text="🔴 Завершённые", callback_data="events_filter:finished"
        ),
    ]

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            *rows,
            nav if nav else [],
            filter_row,
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ],
        ]
    )

    await message.edit_text("📅 Мероприятия:", reply_markup=kb)


# Пагинация
@admin_events_router.callback_query(lambda c: c.data in ("events_prev", "events_next"))
async def cb_events_nav(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    f = fsm(uid)
    st = f.get()

    if callback.data == "events_prev":
        f.set(page=st.get("page", 0) - 1)
    else:
        f.set(page=st.get("page", 0) + 1)

    await show_events(callback.message, uid)
    await callback.answer()


# Фильтры
@admin_events_router.callback_query(lambda c: c.data.startswith("events_filter:"))
async def cb_events_filter(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    mode = callback.data.split(":")[1]

    f = fsm(uid)
    f.set(filter=mode, page=0)

    await show_events(callback.message, uid)
    await callback.answer()


# ================================================================
# КАРТОЧКА МЕРОПРИЯТИЯ
# ================================================================
@admin_events_router.callback_query(lambda c: c.data.startswith("event_card:"))
async def cb_event_card(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

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
    active = ev["is_active"]

    text = (
        f"📌 {name}\n\n"
        f"📅 Дата: {date}\n"
        f"📝 Описание: {desc}\n"
        f"🎯 Тип: {'профильное' if is_prof else 'непрофильное'}\n"
        f"🔵 Статус: {'🟢 Активно' if active else '🔴 Завершено'}"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🏁 Завершить", callback_data=f"event_finish:{tid}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🗑 Удалить", callback_data=f"event_delete:{tid}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ Назад", callback_data="btn_list_events"
                )
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ================================================================
# ЗАВЕРШЕНИЕ МЕРОПРИЯТИЯ
# ================================================================
@admin_events_router.callback_query(lambda c: c.data.startswith("event_finish:"))
async def cb_event_finish(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    tid = int(callback.data.split(":")[1])

    events_raw = load_events()
    events = events_raw.get("events", [])

    ev = next((e for e in events if e["template_id"] == tid), None)
    if not ev:
        await callback.answer("❌ Мероприятие не найдено")
        return

    ev["is_active"] = False
    save_events(events_raw)

    f = fsm(uid)

    # Удаляем карточку мероприятия
    try:
        await callback.message.delete()
    except:
        pass

    # ЛОГ
    await f.log(callback.bot, chat_id, f"🏁 Мероприятие завершено:\n{ev['event_name']}")

    # МЕНЮ
    await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    await callback.answer()


# ================================================================
# УДАЛЕНИЕ МЕРОПРИЯТИЯ (подтверждение)
# ================================================================
@admin_events_router.callback_query(lambda c: c.data.startswith("event_delete:"))
async def cb_event_delete(callback: types.CallbackQuery):
    tid = int(callback.data.split(":")[1])

    events_raw = load_events()
    events = events_raw.get("events", [])

    ev = next((e for e in events if e["template_id"] == tid), None)
    if not ev:
        await callback.answer("❌ Мероприятие не найдено")
        return

    text = f"❗ Удалить мероприятие?\n{ev['event_name']}"

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🗑 Удалить окончательно",
                    callback_data=f"event_delete_confirm:{tid}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ Отмена", callback_data=f"event_card:{tid}"
                )
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ================================================================
# УДАЛЕНИЕ МЕРОПРИЯТИЯ (финал)
# ================================================================
@admin_events_router.callback_query(
    lambda c: c.data.startswith("event_delete_confirm:")
)
async def cb_event_delete_confirm(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    tid = int(callback.data.split(":")[1])

    events_raw = load_events()
    events = events_raw.get("events", [])

    ev = next((e for e in events if e["template_id"] == tid), None)
    event_name = ev["event_name"] if ev else "Неизвестно"

    new_events = [e for e in events if e["template_id"] != tid]
    events_raw["events"] = new_events
    save_events(events_raw)

    f = fsm(uid)

    # Удаляем подтверждение
    try:
        await callback.message.delete()
    except:
        pass

    # ЛОГ
    await f.log(callback.bot, chat_id, f"🗑 Мероприятие удалено:\n{event_name}")

    # МЕНЮ
    await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
    await callback.answer()
