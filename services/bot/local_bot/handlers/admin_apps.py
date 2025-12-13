# handlers/admin_apps.py
"""
Админ: рассмотрение заявок, просмотр фото, начисление баллов.
Новый стиль: единый FSM, чистые сообщения, фото остаются в чате.
"""

import time
from aiogram import Router, types

from services.bot.local_bot.storage import (
    tokens,
    user_info,
    load_applications,
    save_applications,
    load_events,
    save_tokens,
)
from services.bot.local_bot.fsm import fsm
from services.bot.local_bot.keyboards import back_to_menu_kb, build_admin_menu
from services.bot.local_bot.utils import delete_message_safe

admin_apps_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_admin(uid: str) -> bool:
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


def _pending():
    apps = load_applications()
    return [a for a in apps.get("applications", []) if a.get("status") == "pending"]


# ================================================================
# НАЧАЛО РАССМОТРЕНИЯ ЗАЯВОК
# ================================================================
@admin_apps_router.callback_query(lambda c: c.data == "btn_review_applications")
async def cb_review_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    pending = _pending()
    if not pending:
        await callback.message.edit_text(
            "📭 Нет заявок", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    f = fsm(uid)
    f.clear()
    f.set(state="review", index=0)

    await show_application(callback.message, uid, 0)
    await callback.answer()


# ================================================================
# ПОКАЗ ЗАЯВКИ
# ================================================================
async def show_application(message: types.Message, uid: str, index: int):
    f = fsm(uid)
    pending = _pending()

    if not pending or index >= len(pending):
        f.clear()
        await message.edit_text(
            "✅ Все заявки рассмотрены", reply_markup=back_to_menu_kb()
        )
        return

    app = pending[index]

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

    # Обновляем текст заявки
    try:
        msg_main = await message.edit_text(text)
    except:
        msg_main = await message.answer(text)

    chat_id = msg_main.chat.id

    # Фото студента (ОСТАЁТСЯ В ЧАТЕ)
    base_photo = user_info.get(email, {}).get("student_photo_id")
    if base_photo:
        await message.bot.send_photo(chat_id, base_photo, caption="📎 Фото студента")

    # Фото с мероприятия (ОСТАЁТСЯ В ЧАТЕ)
    event_photo = app.get("event_photo_id")
    if event_photo:
        await message.bot.send_photo(
            chat_id, event_photo, caption="📸 Фото с мероприятия"
        )

    # Меню действий
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

    menu_msg = await message.answer("Выберите действие:", reply_markup=kb)

    f.set(menu_id=menu_msg.message_id, index=index)


# ================================================================
# ПРИНЯТИЕ / ОТКЛОНЕНИЕ ЗАЯВКИ
# ================================================================
@admin_apps_router.callback_query(
    lambda c: c.data.startswith(("app_accept:", "app_reject:"))
)
async def cb_process_application(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    action, app_id_str = callback.data.split(":")
    app_id = int(app_id_str)

    apps = load_applications()
    applications = apps.get("applications", [])

    app = next((a for a in applications if a["id"] == app_id), None)
    if not app:
        await callback.answer("❌ Заявка не найдена")
        return

    f = fsm(uid)

    # ------------------------------------------------------------
    # ПРИНЯТИЕ ЗАЯВКИ
    # ------------------------------------------------------------
    if action == "app_accept":
        app["status"] = "approved"

        # Загружаем мероприятие
        events_raw = load_events()
        events = events_raw.get("events", [])
        ev = next((e for e in events if e.get("template_id") == app["event_id"]), None)

        points = 0
        if ev:
            is_prof = ev.get("is_profile", False)
            base = 2
            mult = 1.5 if is_prof else 0.5
            points = int(base * mult)

        # ------------------------------------------------------------
        # НАЧИСЛЕНИЕ БАЛЛОВ СТУДЕНТУ (ИСПРАВЛЕНО)
        # ------------------------------------------------------------

        # 1) Получаем email студента
        email = app.get("user_email")

        # 2) Ищем Telegram ID студента по email
        student_uid = None
        for uid_key, info in tokens.items():
            if info.get("email") == email:
                student_uid = uid_key
                break

        # 3) Если студент не найден — создаём запись
        if not student_uid:
            student_uid = str(app.get("user_id"))  # fallback
            tokens[student_uid] = {
                "email": email,
                "token": None,
                "role": "student",
                "practice_points": 0,
            }

        # 4) Начисляем баллы студенту
        tokens[student_uid]["practice_points"] = (
            tokens[student_uid].get("practice_points", 0) + points
        )

        save_tokens()

        # Уведомляем студента
        try:
            points_text = f"\n⭐️ +{points} баллов" if points > 0 else ""
            await callback.bot.send_message(
                int(student_uid),
                f"✅ Ваша заявка на «{app['event_name']}» одобрена!{points_text}",
            )
        except:
            pass

        log_text = (
            f"✅ Заявка одобрена:\n"
            f"{app['event_name']}\n"
            f"👤 {email}\n"
            f"⭐️ +{points} баллов"
        )

    # ------------------------------------------------------------
    # ОТКЛОНЕНИЕ ЗАЯВКИ
    # ------------------------------------------------------------
    else:
        app["status"] = "rejected"

        try:
            await callback.bot.send_message(
                app["user_id"],
                f"❌ Ваша заявка на «{app['event_name']}» отклонена.",
            )
        except:
            pass

        log_text = (
            f"❌ Заявка отклонена:\n"
            f"{app['event_name']}\n"
            f"👤 {app.get('user_email')}"
        )

    save_applications(apps)

    # Удаляем меню действий
    menu_id = f.get().get("menu_id")
    if menu_id:
        await delete_message_safe(chat_id, menu_id, callback.bot)
        f.set(menu_id=None)

    # ЛОГ
    await f.log(callback.bot, chat_id, log_text)

    # Проверяем есть ли ещё заявки
    pending = _pending()
    if not pending:
        f.clear()
        await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
        await callback.answer()
        return

    # Показываем следующую заявку
    current_index = f.get().get("index", 0)
    f.set(state="review", index=current_index)

    await show_application(callback.message, uid, current_index)
    await callback.answer()
