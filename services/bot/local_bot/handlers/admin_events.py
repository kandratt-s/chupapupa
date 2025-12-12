# handlers/admin_events.py
"""
Админ: создание мероприятий, список, фильтры, просмотр, завершение.
"""

import time
import asyncio
from aiogram import Router, types

from services.bot.local_bot.storage import (
    tokens,
    load_events,
    save_events,
)
from services.bot.local_bot.fsm import get_state, set_state, clear_state, delete_prompts
from services.bot.local_bot.keyboards import (
    cancel_kb,
    back_to_menu_kb,
)
from services.bot.local_bot.utils import delete_message_safe

admin_events_router = Router()


def is_admin(uid: str) -> bool:
    """Проверка роли администратора."""
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


# ===============================================================
# СОЗДАНИЕ МЕРОПРИЯТИЯ
# ===============================================================


@admin_events_router.callback_query(lambda c: c.data == "btn_create_event")
async def cb_create_event(callback: types.CallbackQuery):
    """Начало создания мероприятия."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    clear_state(uid)

    st = {"state": "event_name", "prompts": [], "ts": time.time()}
    set_state(uid, st)

    msg = await callback.message.edit_text(
        "📝 Введите название мероприятия:", reply_markup=cancel_kb()
    )
    st["prompts"].append(msg.message_id)
    set_state(uid, st)

    await callback.answer()


@admin_events_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "event_name"
)
async def event_name(message: types.Message):
    """Ввод названия."""
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

    st = get_state(uid)
    await delete_prompts(message.bot, uid, message.chat.id)

    st["name"] = name
    st["state"] = "event_description"
    set_state(uid, st)

    msg = await message.answer(
        "📝 Введите описание мероприятия:", reply_markup=cancel_kb()
    )
    st["prompts"].append(msg.message_id)
    set_state(uid, st)


@admin_events_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "event_description"
)
async def event_description(message: types.Message):
    """Ввод описания."""
    uid = str(message.from_user.id)
    desc = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    st = get_state(uid)
    await delete_prompts(message.bot, uid, message.chat.id)

    st["description"] = desc
    st["state"] = "event_profile"
    set_state(uid, st)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Профильное", callback_data="event_prof:yes"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Непрофильное", callback_data="event_prof:no"
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
    st["prompts"].append(msg.message_id)
    set_state(uid, st)


@admin_events_router.callback_query(lambda c: c.data.startswith("event_prof:"))
async def event_profile(callback: types.CallbackQuery):
    """Выбор профильности."""
    uid = str(callback.from_user.id)
    st = get_state(uid)

    choice = callback.data.split(":")[1]
    st["is_profile"] = choice == "yes"
    st["state"] = "event_date"
    set_state(uid, st)

    msg = await callback.message.edit_text(
        "📅 Укажите дату (ДД-ММ-ГГГГ):", reply_markup=cancel_kb()
    )
    st["prompts"].append(msg.message_id)
    set_state(uid, st)

    await callback.answer()


@admin_events_router.message(
    lambda m: get_state(str(m.from_user.id)).get("state") == "event_date"
)
async def event_date(message: types.Message):
    """Ввод даты."""
    uid = str(message.from_user.id)
    date_text = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    try:
        dt = time.strptime(date_text, "%d-%m-%Y")
        ts = int(time.mktime(dt))
    except:
        err = await message.answer("❌ Неверный формат. Пример: 31-12-2025")
        await asyncio.sleep(2)
        await delete_message_safe(err.chat.id, err.message_id)
        return

    st = get_state(uid)
    await delete_prompts(message.bot, uid, message.chat.id)

    events_raw = load_events()
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
    save_events(events_raw)

    clear_state(uid)

    await message.answer(
        f"✅ Мероприятие создано:\n{st['name']}\n📅 {date_text}",
        reply_markup=back_to_menu_kb(),
    )


# ===============================================================
# СПИСОК МЕРОПРИЯТИЙ
# ===============================================================

PAGE_SIZE = 10


@admin_events_router.callback_query(lambda c: c.data == "btn_list_events")
async def cb_list_events(callback: types.CallbackQuery):
    """Показ списка мероприятий."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    events_raw = load_events()
    events = events_raw.get("events", [])

    if not events:
        await callback.message.edit_text(
            "📭 Мероприятий нет", reply_markup=back_to_menu_kb()
        )
        return

    events_sorted = sorted(
        events, key=lambda e: e.get("event_date_ts", 0), reverse=True
    )

    st = {
        "state": "admin_events_list",
        "events": events_sorted,
        "page": 0,
        "filter": "all",
    }
    set_state(uid, st)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


async def show_admin_events_page(message: types.Message, uid: str, page: int):
    """Показ страницы списка мероприятий."""
    st = get_state(uid)
    events = st.get("events", [])
    flt = st.get("filter", "all")

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
        await message.edit_text(
            "📭 Нет мероприятий по выбранному фильтру", reply_markup=kb
        )
        return

    total = len(events_filtered)
    max_page = (total - 1) // PAGE_SIZE

    page = max(0, min(page, max_page))

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    chunk = events_filtered[start:end]

    lines = []
    for idx, ev in enumerate(chunk, start=start + 1):
        name = ev.get("event_name", "(без названия)")
        date = ev.get("event_date", "-")
        is_prof = ev.get("is_profile", False)
        is_active = ev.get("is_active", True)

        status_circle = "🟢" if is_active else "🔴"
        prof_text = "профильное" if is_prof else "непрофильное"

        lines.append(f"{idx}. {status_circle} {name} — {date} ({prof_text})")

    text = "📋 Список мероприятий:\n\n" + "\n".join(lines)
    text += f"\n\nСтраница {page + 1} из {max_page + 1}"

    filter_row = [
        types.InlineKeyboardButton(text="🟢 Активные", callback_data="flt_active"),
        types.InlineKeyboardButton(text="🔴 Завершённые", callback_data="flt_inactive"),
        types.InlineKeyboardButton(text="📋 Все", callback_data="flt_all"),
    ]

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

    await message.edit_text(text, reply_markup=kb)

    st["page"] = page
    set_state(uid, st)


# Фильтры
@admin_events_router.callback_query(lambda c: c.data == "flt_active")
async def flt_active(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)

    if st.get("filter") == "active":
        await callback.answer("Уже выбраны активные")
        return

    st["filter"] = "active"
    st["page"] = 0
    set_state(uid, st)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


@admin_events_router.callback_query(lambda c: c.data == "flt_inactive")
async def flt_inactive(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)

    if st.get("filter") == "inactive":
        await callback.answer("Уже выбраны завершённые")
        return

    st["filter"] = "inactive"
    st["page"] = 0
    set_state(uid, st)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


@admin_events_router.callback_query(lambda c: c.data == "flt_all")
async def flt_all(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)

    if st.get("filter") == "all":
        await callback.answer("Уже выбраны все")
        return

    st["filter"] = "all"
    st["page"] = 0
    set_state(uid, st)

    await show_admin_events_page(callback.message, uid, 0)
    await callback.answer()


# Навигация
@admin_events_router.callback_query(lambda c: c.data == "admin_events_prev")
async def admin_events_prev(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)

    if st.get("state") != "admin_events_list":
        await callback.answer()
        return

    await show_admin_events_page(callback.message, uid, st.get("page", 0) - 1)
    await callback.answer()


@admin_events_router.callback_query(lambda c: c.data == "admin_events_next")
async def admin_events_next(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    st = get_state(uid)

    if st.get("state") != "admin_events_list":
        await callback.answer()
        return

    await show_admin_events_page(callback.message, uid, st.get("page", 0) + 1)
    await callback.answer()


# ===============================================================
# ЗАВЕРШЕНИЕ МЕРОПРИЯТИЯ
# ===============================================================


@admin_events_router.callback_query(lambda c: c.data == "btn_finish_event")
async def cb_finish_event(callback: types.CallbackQuery):
    """Показ списка активных мероприятий для завершения."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    events_raw = load_events()
    events = events_raw.get("events", [])

    active = [e for e in events if e.get("is_template") and e.get("is_active", True)]

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
                        text=f"{name} — {date}", callback_data=f"finish_event:{idx}"
                    )
                ]
            )

    rows.append(
        [types.InlineKeyboardButton(text="◀️ В меню", callback_data="btn_back_to_menu")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text(
        "🏁 Выберите мероприятие для завершения:", reply_markup=kb
    )
    await callback.answer()


@admin_events_router.callback_query(lambda c: c.data.startswith("finish_event:"))
async def finish_event(callback: types.CallbackQuery):
    """Завершение выбранного мероприятия."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
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

    events[idx]["is_active"] = False
    save_events(events_raw)

    name = events[idx].get("event_name", "(без названия)")

    await callback.message.edit_text(
        f"✅ Мероприятие «{name}» завершено", reply_markup=back_to_menu_kb()
    )
    await callback.answer()
