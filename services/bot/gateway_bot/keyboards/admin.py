from aiogram import types


def build_admin_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📥 Рассмотреть заявки",
                    callback_data="btn_review_applications",
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
