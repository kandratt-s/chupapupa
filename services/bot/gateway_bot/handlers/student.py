"""
Студент: список мероприятий, карточка, отметка, мои заявки.
Полностью переписано под API Gateway.
"""

import time
import asyncio
import os
import httpx
from aiogram import Router, types

from services.bot.gateway_bot.fsm.fsm import fsm
from services.bot.gateway_bot.keyboards import (
    back_to_menu_kb,
    build_user_menu,
)
from services.bot.gateway_bot.utils.utils import delete_message_safe
from services.bot.gateway_bot.utils.photos import download_telegram_photo
from services.bot.gateway_bot.config import API_GATEWAY_URL, PHOTOS_DIR, TIMEOUT

from services.bot.gateway_bot.api.events import api_get_events, api_get_event
from services.bot.gateway_bot.api.attendance import (
    api_create_application,
    api_get_my_applications,
)
from services.bot.gateway_bot.api.storage import api_upload_photo


student_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_authenticated(session: dict) -> bool:
    return bool(session.get("token"))


# ================================================================
# СПИСОК МЕРОПРИЯТИЙ
# ================================================================
@student_router.callback_query(lambda c: c.data == "btn_events")
async def cb_events(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)
    session = f.get()

    if not is_authenticated(session):
        await f.show_menu(
            callback.bot, chat_id, "❌ Сначала авторизуйтесь", back_to_menu_kb()
        )
        await callback.answer()
        return

    token = session["token"]

    events = await api_get_events(token)
    if not events:
        await f.show_menu(
            callback.bot, chat_id, "📭 Нет активных мероприятий", back_to_menu_kb()
        )
        await callback.answer()
        return

    rows = []
    for ev in events:
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{ev['name']} — {ev['date']}",
                    callback_data=f"view_event:{ev['id']}",
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
    f = fsm(uid)
    session = f.get()

    if not is_authenticated(session):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    token = session["token"]
    event_id = callback.data.split(":")[1]

    ev = await api_get_event(token, event_id)
    if not ev:
        await callback.answer("❌ Мероприятие не найдено")
        return

    base_points = 2
    multiplier = 1.5 if ev["is_profile"] else 0.5
    points = int(base_points * multiplier)

    text = (
        f"📌 {ev['name']}\n\n"
        f"📅 Дата: {ev['date']}\n"
        f"📝 Описание: {ev['description']}\n"
        f"🎯 Тип: {'профильное' if ev['is_profile'] else 'непрофильное'}\n"
        f"⭐ Баллы: {points}"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📸 Отметиться", callback_data=f"attend_event:{event_id}"
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
    f = fsm(uid)
    session = f.get()

    if not is_authenticated(session):
        await callback.answer("❌ Сначала авторизуйтесь")
        return

    event_id = callback.data.split(":")[1]

    f.clear()
    f.set(state="waiting_event_photo", event_id=event_id)

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
    session = f.get()

    if not is_authenticated(session):
        await f.show_menu(
            message.bot, chat_id, "❌ Сначала авторизуйтесь", build_user_menu()
        )
        return

    token = session["token"]
    backend_user_id = session["backend_user_id"]
    event_id = session["event_id"]

    await f.clear_prompts(message.bot, chat_id)

    # Скачиваем фото
    local_path = await download_telegram_photo(message, PHOTOS_DIR)

    # Загружаем фото в Object Storage
    uploaded = await api_upload_photo(token, local_path)
    if not uploaded:
        err = await message.answer("❌ Ошибка загрузки фото")
        await asyncio.sleep(1.2)
        await delete_message_safe(chat_id, err.message_id)
        return

    # Создаём заявку
    created = await api_create_application(
        token=token,
        user_id=backend_user_id,
        event_id=event_id,
        photo_url=uploaded["url"],
    )

    f.clear()

    if not created:
        await f.show_menu(
            message.bot, chat_id, "❌ Ошибка создания заявки", build_user_menu()
        )
        return

    await f.log(
        message.bot,
        chat_id,
        f"✅ Вы отметились на мероприятии!\n⏳ Заявка на рассмотрении",
    )

    await f.show_menu(message.bot, chat_id, "🎓 Меню студента", build_user_menu())


# ================================================================
# МОИ ЗАЯВКИ
# ================================================================
@student_router.callback_query(lambda c: c.data == "btn_my_applications")
async def cb_my_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    f = fsm(uid)
    session = f.get()

    if not is_authenticated(session):
        await f.show_menu(
            callback.bot, chat_id, "❌ Сначала авторизуйтесь", back_to_menu_kb()
        )
        await callback.answer()
        return

    token = session["token"]
    backend_user_id = session["backend_user_id"]

    apps = await api_get_my_applications(token, backend_user_id)

    if not apps:
        await f.show_menu(
            callback.bot, chat_id, "📭 У вас пока нет заявок", back_to_menu_kb()
        )
        await callback.answer()
        return

    lines = []
    for i, app in enumerate(apps, start=1):
        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(
            app["status"], "❓"
        )
        text = {
            "pending": "На рассмотрении",
            "approved": "Одобрена",
            "rejected": "Отклонена",
        }.get(app["status"])
        lines.append(f"{i}. {emoji} {app['event_name']} — {text}")

    await callback.message.edit_text(
        "📊 Ваши заявки:\n\n" + "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
