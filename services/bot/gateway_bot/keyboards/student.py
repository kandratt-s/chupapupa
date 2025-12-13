from aiogram import types


def build_user_menu():
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
