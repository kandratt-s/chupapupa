"""
Единый стиль клавиатур для бота.
Минимализм, аккуратные иконки, компактные кнопки.
"""

from aiogram import types
from services.bot.local_bot.storage import load_applications


def btn(text, data):
    return types.InlineKeyboardButton(text=text, callback_data=data)


def ikb(rows):
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


# -------------------------------------------------------------
# Базовые клавиатуры
# -------------------------------------------------------------
def cancel_kb():
    return ikb([[btn("❌ Отменить", "btn_cancel")]])


def login_kb():
    return ikb([[btn("🔐 Войти", "btn_login")]])


def back_to_menu_kb():
    return ikb([[btn("◀️ В меню", "btn_back_to_menu")]])


# -------------------------------------------------------------
# Меню студента
# -------------------------------------------------------------
def build_user_menu():
    return ikb(
        [
            [btn("📅 Мероприятия", "btn_events")],
            [btn("📝 Мои заявки", "btn_my_applications")],
            [btn("👤 Профиль", "btn_profile")],
            [btn("🚪 Выйти", "btn_logout")],
        ]
    )


# -------------------------------------------------------------
# Меню администратора
# -------------------------------------------------------------
def build_admin_menu():
    apps = load_applications()
    pending = len(
        [a for a in apps.get("applications", []) if a.get("status") == "pending"]
    )

    return ikb(
        [
            [btn("➕ Создать мероприятие", "btn_create_event")],
            [btn("📅 Мероприятия", "btn_list_events")],
            [btn(f"📥 Заявки ({pending})", "btn_review_applications")],
            [btn("👥 Создать пользователя", "btn_admin_register")],
            [btn("👤 Профиль", "btn_profile")],
            [btn("🚪 Выйти", "btn_logout")],
        ]
    )
