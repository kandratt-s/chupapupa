import json
import os
import re
import time
from email_validator import validate_email, EmailNotValidError
from aiogram import types
import hashlib

from config import (
    USER_STATES_PATH,
    PHOTOS_DIR,
)


def load(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save(dictionary, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=3, ensure_ascii=False)


def validate_mail(email: str) -> str | None:
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError:
        return None


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not (re.search(r"[A-Z]", password) or re.search(r"[a-z]", password)):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True


def get_display_name(
    user_id: str, tokens: dict, user_info: dict, tg_user: types.User | None = None
) -> str:
    tok = tokens.get(user_id) or {}
    email = tok.get("email")
    if email and email in user_info:
        fi = user_info.get(email, {})
        fn = fi.get("first_name") or ""
        if fn:
            return fn
    if tg_user:
        return getattr(tg_user, "first_name", "Пользователь") or "Пользователь"
    return "Пользователь"


def clear_user_state(user_states: dict, user_id: str):
    state = user_states.get(user_id)
    if state:
        photo_paths = state.get("photo_paths", [])
        for photo_path in photo_paths:
            if photo_path and os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except Exception:
                    pass
        user_states.pop(user_id, None)
        save(user_states, USER_STATES_PATH)


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def ensure_photos_dir():
    os.makedirs(PHOTOS_DIR, exist_ok=True)
