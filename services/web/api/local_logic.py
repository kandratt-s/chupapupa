from datetime import datetime
from typing import List, Dict, Any, Optional

from services.web.api.local_storage import (
    load_users,
    save_users,
    load_events,
    save_events,
    load_applications,
    save_applications,
)

# ---------------------------------------------------------
# USERS
# ---------------------------------------------------------


def local_register_user(
    name: str, surname: str, email: str, role: str, password: str
) -> Dict[str, Any]:
    users = load_users()
    user_id = len(users) + 1

    user = {
        "id": user_id,
        "name": name,
        "surname": surname,
        "email": email,
        "role": role,
        "password": password,
        "points": 0,
    }

    users.append(user)
    save_users(users)
    return user


def local_login(email: str, password: str) -> Optional[Dict[str, Any]]:
    users = load_users()
    for u in users:
        if u["email"] == email and u["password"] == password:
            return u
    return None


def local_get_user(user_id: int) -> Optional[Dict[str, Any]]:
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None


def local_get_all_users() -> List[Dict[str, Any]]:
    return load_users()


def local_delete_user(user_id: int) -> None:
    users = load_users()
    users = [u for u in users if u["id"] != user_id]
    save_users(users)


def local_add_points(user_id: int, points: int) -> None:
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["points"] = u.get("points", 0) + points
            break
    save_users(users)


# ---------------------------------------------------------
# EVENTS
# ---------------------------------------------------------


def local_admin_create_event(
    name: str, description: str, is_profile: bool, date_str: str
) -> Dict[str, Any]:
    events = load_events()
    event_id = len(events) + 1

    event = {
        "id": event_id,
        "name": name,
        "description": description,
        "date": date_str,
        "is_profile": is_profile,
        "is_active": True,
    }

    events.append(event)
    save_events(events)
    return event


def local_get_event(event_id: int) -> Optional[Dict[str, Any]]:
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            return e
    return None


def local_get_all_events() -> List[Dict[str, Any]]:
    return load_events()


def local_get_active_events() -> List[Dict[str, Any]]:
    return [e for e in load_events() if e["is_active"]]


def local_admin_deactivate_event(event_id: int) -> None:
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            e["is_active"] = False
            break
    save_events(events)


def local_admin_delete_event(event_id: int) -> None:
    events = load_events()
    events = [e for e in events if e["id"] != event_id]
    save_events(events)


# ---------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------


def local_create_application(
    user_id: int, event_id: int, photo_path: str | None
) -> Dict[str, Any]:
    apps = load_applications()
    ev = local_get_event(event_id)

    app_id = len(apps) + 1

    app = {
        "id": app_id,
        "user_id": user_id,
        "event_id": event_id,
        "event_name": ev["name"] if ev else "",
        "photo_path": photo_path,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    apps.append(app)
    save_applications(apps)
    return app


def local_get_my_applications(user_id: int) -> List[Dict[str, Any]]:
    apps = load_applications()
    return [a for a in apps if a["user_id"] == user_id]


def local_get_all_applications() -> List[Dict[str, Any]]:
    return load_applications()


def local_update_application_status(app_id: int, status: str) -> None:
    apps = load_applications()
    for a in apps:
        if a["id"] == app_id:
            a["status"] = status
            break
    save_applications(apps)
