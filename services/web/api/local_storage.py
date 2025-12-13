# services/web/api/local_storage.py

import json
import os
from typing import Any, List, Dict

from services.web.config import USERS_PATH, EVENTS_PATH, APPLICATIONS_PATH


def _ensure_file(path: str, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=3, ensure_ascii=False)


def load_users() -> List[Dict[str, Any]]:
    _ensure_file(USERS_PATH, [])
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users: List[Dict[str, Any]]):
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=3, ensure_ascii=False)


def load_events() -> List[Dict[str, Any]]:
    _ensure_file(EVENTS_PATH, [])
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events(events: List[Dict[str, Any]]):
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=3, ensure_ascii=False)


def load_applications() -> List[Dict[str, Any]]:
    _ensure_file(APPLICATIONS_PATH, [])
    with open(APPLICATIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_applications(apps: List[Dict[str, Any]]):
    with open(APPLICATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=3, ensure_ascii=False)
