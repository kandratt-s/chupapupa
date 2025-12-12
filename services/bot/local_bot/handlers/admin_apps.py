# handlers/admin_apps.py
"""
Админ: рассмотрение заявок, просмотр фото, начисление баллов.
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
from services.bot.local_bot.fsm import get_state, set_state, clear_state
from services.bot.local_bot.keyboards import back_to_menu_kb
from services.bot.local_bot.utils import delete_message_safe

admin_apps_router = Router()


def is_admin(uid: str) -> bool:
    """Проверка роли администратора."""
    u = tokens.get(uid)
    return bool(u and u.get("role") == "admin")


# ===============================================================
# НАЧАЛО РАССМОТРЕНИЯ ЗАЯВОК
# ===============================================================


@admin_apps_router.callback_query(lambda c: c.data == "btn_review_applications")
async def cb_review_applications(callback: types.CallbackQuery):
    """Показ первой заявки."""
    uid = str(callback.from_user.id)

    if not is_admin(uid):
        await callback.answer("❌ Только администратор")
        return

    apps = load_applications()
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    if not pending:
        await callback.message.edit_text(
            "📭 Нет заявок", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    clear_state(uid)
    set_state(uid, {"state": "review", "index": 0})

    await show_application(callback.message, uid, 0)
    await callback.answer()


# ===============================================================
# ПОКАЗ ЗАЯВКИ
# ===============================================================


async def show_application(message: types.Message, uid: str, index: int):
    """Показ одной заявки + фото + кнопки."""
    apps = load_applications()
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    if not pending or index >= len(pending):
        clear_state(uid)
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

    # Обновляем текст заявки
    try:
        msg_main = await message.edit_text(text)
    except:
        msg_main = await message.answer(text)

    chat_id = msg_main.chat.id

    # Фото студента
    base_photo = user_info.get(email, {}).get("student_photo_id")
    if base_photo:
        await message.bot.send_photo(chat_id, base_photo, caption="📎 Фото студента")

    # Фото с мероприятия
    event_photo = app.get("event_photo_id")
    if event_photo:
        await message.bot.send_photo(
            chat_id, event_photo, caption="📸 Фото с мероприятия"
        )

    # Меню действий
    menu_msg = await message.answer("Выберите действие:", reply_markup=kb)

    st = get_state(uid)
    st["menu_message_id"] = menu_msg.message_id
    st["index"] = index
    set_state(uid, st)


# ===============================================================
# ПРИНЯТИЕ / ОТКЛОНЕНИЕ ЗАЯВКИ
# ===============================================================


@admin_apps_router.callback_query(
    lambda c: c.data.startswith(("app_accept:", "app_reject:"))
)
async def cb_process_application(callback: types.CallbackQuery):
    """Обработка заявки: принять или отклонить."""
    uid = str(callback.from_user.id)

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

    # -----------------------------------------------------------
    # Принятие заявки
    # -----------------------------------------------------------
    if action == "app_accept":
        app["status"] = "approved"

        events_raw = load_events()
        events = events_raw.get("events", [])
        ev = next((e for e in events if e.get("template_id") == app["event_id"]), None)

        if ev:
            is_prof = ev.get("is_profile", False)
            base = 2
            mult = 1.5 if is_prof else 0.5
            points = int(base * mult)

            email = app.get("user_email") or tokens.get(str(app["user_id"]), {}).get(
                "email"
            )

            if email:
                student_key = next(
                    (k for k, v in tokens.items() if v.get("email") == email), None
                )

                if student_key:
                    tokens[student_key]["practice_points"] = (
                        tokens[student_key].get("practice_points", 0) + points
                    )
                else:
                    tokens[email] = {
                        "email": email,
                        "token": None,
                        "role": "student",
                        "practice_points": points,
                    }

                save_tokens()

        # Уведомление студента
        try:
            await callback.bot.send_message(
                app["user_id"],
                f"✅ Ваша заявка на мероприятие '{app['event_name']}' одобрена!",
            )
        except:
            pass

        admin_text = f"✅ Участие подтверждено:\n{app['event_name']}"

    # -----------------------------------------------------------
    # Отклонение заявки
    # -----------------------------------------------------------
    else:
        app["status"] = "rejected"

        try:
            await callback.bot.send_message(
                app["user_id"],
                f"❌ Ваша заявка на мероприятие '{app['event_name']}' отклонена.",
            )
        except:
            pass

        admin_text = f"❌ Участие отклонено:\n{app['event_name']}"

    save_applications(apps)

    # Удаляем меню действий
    st = get_state(uid)
    menu_id = st.get("menu_message_id")
    if menu_id:
        await delete_message_safe(callback.message.chat.id, menu_id)
        st["menu_message_id"] = None

    await callback.message.answer(admin_text)

    # Переход к следующей заявке
    apps = load_applications()
    pending = [a for a in apps.get("applications", []) if a.get("status") == "pending"]

    if not pending:
        clear_state(uid)
        await callback.message.answer(
            "✅ Все заявки рассмотрены", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    current_index = st.get("index", 0)
    set_state(uid, {"state": "review", "index": current_index})

    await show_application(callback.message, uid, current_index)
    await callback.answer()
