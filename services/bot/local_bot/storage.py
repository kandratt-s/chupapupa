# storage.py
"""
Работа с JSON-хранилищами: загрузка и сохранение.
"""

from typing import Any, Dict
from services.bot.local_bot.utils import load, save

from services.bot.local_bot.config import (
    USER_TOKENS_PATH,
    USER_INFO_PATH,
    USER_STATES_PATH,
    APPLICATIONS_PATH,
    EVENTS_PATH,
)

# Глобальные "таблицы"
tokens: Dict[str, Dict[str, Any]] = load(USER_TOKENS_PATH) or {}
user_info: Dict[str, Dict[str, Any]] = load(USER_INFO_PATH) or {}
user_states: Dict[str, Dict[str, Any]] = load(USER_STATES_PATH) or {}


def save_tokens() -> None:
    """Сохранить таблицу токенов."""
    save(tokens, USER_TOKENS_PATH)


def save_user_info() -> None:
    """Сохранить таблицу пользователей."""
    save(user_info, USER_INFO_PATH)


def save_user_states() -> None:
    """Сохранить FSM-состояния."""
    save(user_states, USER_STATES_PATH)


def load_applications() -> Dict[str, Any]:
    """Загрузить все заявки."""
    return load(APPLICATIONS_PATH) or {}


def save_applications(data: Dict[str, Any]) -> None:
    """Сохранить все заявки."""
    save(data, APPLICATIONS_PATH)


def load_events() -> Dict[str, Any]:
    """Загрузить все мероприятия."""
    return load(EVENTS_PATH) or {}


def save_events(data: Dict[str, Any]) -> None:
    """Сохранить все мероприятия."""
    save(data, EVENTS_PATH)
