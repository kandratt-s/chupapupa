# fsm.py
"""
Утилиты для работы с FSM-состояниями пользователей.
"""

from typing import Any, Dict
from aiogram import Bot

from services.bot.local_bot.storage import user_states, save_user_states
from services.bot.local_bot.utils import (
    clear_user_state as _clear_user_state,
    safe_log_error,
)


def get_state(uid: str) -> Dict[str, Any]:
    """Вернуть состояние пользователя или пустой словарь."""
    return user_states.get(uid, {})


def set_state(uid: str, state: Dict[str, Any]) -> None:
    """Сохранить состояние пользователя."""
    user_states[uid] = state
    save_user_states()


def clear_state(uid: str) -> None:
    """Очистить FSM-память пользователя."""
    _clear_user_state(user_states, uid)
    save_user_states()


async def delete_prompts(bot, uid, chat_id):
    st = user_states.get(uid, {})
    prompts = st.get("prompts", [])

    for msg_id in prompts:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            print(f"[WARN] delete_prompts: {e}")

    st["prompts"] = []
    user_states[uid] = st
    save_user_states()
