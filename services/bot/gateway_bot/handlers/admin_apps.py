"""
Админ: рассмотрение заявок, просмотр фото, начисление баллов.
Полностью переписано под API Gateway.
"""

from aiogram import Router, types
from services.bot.gateway_bot.fsm.fsm import fsm
from services.bot.gateway_bot.keyboards import back_to_menu_kb, build_admin_menu
from services.bot.gateway_bot.utils.utils import delete_message_safe

from services.bot.gateway_bot.api.attendance import (
    api_get_pending_applications,
    api_get_application,
    api_approve_application,
    api_reject_application,
)
from services.bot.gateway_bot.api.api import api_get_user
from services.bot.gateway_bot.api.events import api_get_event
from services.bot.gateway_bot.api.statistics import api_add_points

admin_apps_router = Router()


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ================================================================
def is_admin(session: dict) -> bool:
    return session.get("role") == "admin"


# ================================================================
# НАЧАЛО РАССМОТРЕНИЯ ЗАЯВОК
# ================================================================
@admin_apps_router.callback_query(lambda c: c.data == "btn_review_applications")
async def cb_review_applications(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    f = fsm(uid)
    session = f.get()

    if not is_admin(session):
        await callback.answer("❌ Только администратор")
        return

    token = session["token"]

    pending = await api_get_pending_applications(token)
    if not pending:
        await callback.message.edit_text(
            "📭 Нет заявок", reply_markup=back_to_menu_kb()
        )
        await callback.answer()
        return

    f.clear()
    f.set(state="review", index=0)

    await show_application(callback.message, uid, 0)
    await callback.answer()


# ================================================================
# ПОКАЗ ЗАЯВКИ
# ================================================================
async def show_application(message: types.Message, uid: str, index: int):
    f = fsm(uid)
    session = f.get()
    token = session["token"]

    pending = await api_get_pending_applications(token)

    if not pending or index >= len(pending):
        f.clear()
        await message.edit_text(
            "✅ Все заявки рассмотрены", reply_markup=back_to_menu_kb()
        )
        return

    app = pending[index]

    # Загружаем профиль студента
    user = await api_get_user(token, app["user_id"])
    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

    text = (
        f"🎯 Мероприятие: {app['event_name']}\n"
        f"👤 Участник: {full_name}\n"
        f"📧 Email: {user.get('email')}\n\n"
        f"Заявка {index + 1} из {len(pending)}"
    )

    try:
        msg_main = await message.edit_text(text)
    except:
        msg_main = await message.answer(text)

    chat_id = msg_main.chat.id

    # Фото студента
    if user.get("photo_url"):
        await message.bot.send_photo(
            chat_id, user["photo_url"], caption="📎 Фото студента"
        )

    # Фото с мероприятия
    if app.get("photo_url"):
        await message.bot.send_photo(
            chat_id, app["photo_url"], caption="📸 Фото с мероприятия"
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
    admin_uid = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    f = fsm(admin_uid)
    session = f.get()

    if not is_admin(session):
        await callback.answer("❌ Только администратор")
        return

    token = session["token"]

    action, app_id_str = callback.data.split(":")
    app_id = app_id_str

    # Загружаем заявку
    app = await api_get_application(token, app_id)
    if not app:
        await callback.answer("❌ Заявка не найдена")
        return

    # Загружаем мероприятие
    event = await api_get_event(token, app["event_id"])

    # Рассчитываем баллы
    base = 2
    mult = 1.5 if event["is_profile"] else 0.5
    points = int(base * mult)

    # ------------------------------------------------------------
    # ПРИНЯТИЕ
    # ------------------------------------------------------------
    if action == "app_accept":
        await api_approve_application(token, app_id)

        # Начисляем баллы
        await api_add_points(token, app["user_id"], points)

        # Уведомляем студента
        try:
            await callback.bot.send_message(
                app["telegram_id"],
                f"✅ Ваша заявка на «{app['event_name']}» одобрена!\n⭐️ +{points} баллов",
            )
        except:
            pass

        log_text = (
            f"✅ Заявка одобрена:\n"
            f"{app['event_name']}\n"
            f"👤 {app['user_email']}\n"
            f"⭐️ +{points} баллов"
        )

    # ------------------------------------------------------------
    # ОТКЛОНЕНИЕ
    # ------------------------------------------------------------
    else:
        await api_reject_application(token, app_id)

        try:
            await callback.bot.send_message(
                app["telegram_id"],
                f"❌ Ваша заявка на «{app['event_name']}» отклонена.",
            )
        except:
            pass

        log_text = (
            f"❌ Заявка отклонена:\n" f"{app['event_name']}\n" f"👤 {app['user_email']}"
        )

    # Удаляем меню действий
    menu_id = f.get().get("menu_id")
    if menu_id:
        await delete_message_safe(chat_id, menu_id, callback.bot)
        f.set(menu_id=None)

    # ЛОГ
    await f.log(callback.bot, chat_id, log_text)

    # Проверяем есть ли ещё заявки
    pending = await api_get_pending_applications(token)
    if not pending:
        f.clear()
        await f.show_menu(callback.bot, chat_id, "👑 Админ‑панель", build_admin_menu())
        await callback.answer()
        return

    # Показываем следующую заявку
    current_index = f.get().get("index", 0)
    f.set(state="review", index=current_index)

    await show_application(callback.message, admin_uid, current_index)
    await callback.answer()
