# keyboards.py
"""
Готовые наборы инлайн-клавиатур.
"""

from aiogram import types
from services.bot.local_bot.storage import load_applications


def cancel_kb() -> types.InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой отмены."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel")]
        ]
    )


def login_kb() -> types.InlineKeyboardMarkup:
    """Клавиатура с кнопкой входа."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔐 Войти", callback_data="btn_login")]
        ]
    )


def back_to_menu_kb() -> types.InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в главное меню."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="◀️ В меню", callback_data="btn_back_to_menu"
                )
            ]
        ]
    )


def build_user_menu() -> types.InlineKeyboardMarkup:
    """Главное меню студента."""
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


def build_admin_menu() -> types.InlineKeyboardMarkup:
    """Главное меню администратора с количеством необработанных заявок."""
    apps = load_applications()
    applications = apps.get("applications", [])
    pending = len([a for a in applications if a.get("status") == "pending"])

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
                    text=f"📥 Рассмотреть заявки ({pending})",
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
                    text="👥 Студенты", callback_data="btn_admin_students"
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
