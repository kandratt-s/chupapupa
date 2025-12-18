import os
from datetime import datetime
from typing import Any

import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")


def _auth_headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _normalize_role(role: str | None) -> str:
    """
    Бэкенд отдаёт роль "user" для студентов. Приводим к ожидаемому "student".
    """
    if not role:
        return "student"
    role_lower = role.lower()
    if role_lower == "user":
        return "student"
    return role_lower


def _normalize_event(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("event_id") or data.get("id"),
        "name": data.get("name"),
        "date": data.get("date"),
        "description": data.get("opisanie") or data.get("description"),
        "is_profile": data.get("profilnoe") or data.get("is_profile") or False,
        "is_active": data.get("active", True),
    }


def _normalize_user(data: dict[str, Any]) -> dict[str, Any]:
    role = _normalize_role(data.get("role") or data.get("user_role"))
    return {
        "id": data.get("user_id") or data.get("id"),
        "name": data.get("first_name") or data.get("name"),
        "surname": data.get("last_name") or data.get("surname"),
        "email": data.get("hse_email") or data.get("email"),
        "points": data.get("practice_points") or data.get("points", 0),
        "photo_path": data.get("photo_path"),
        "role": role,
    }


async def _fetch_auth_role(client: httpx.AsyncClient, token: str | None, user_id: int | None) -> str | None:
    if not user_id:
        return None
    resp = await client.get(f"/auth/{user_id}", headers=_auth_headers(token))
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("role")


async def api_login(email: str, password: str) -> dict | None:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.post("/auth/login-email", json={"email": email, "password": password})
        if resp.status_code != 200:
            return None
        tokens = resp.json()
        access_token = tokens.get("access_token")
        verify = await client.get("/auth/verify-token", headers=_auth_headers(access_token))
        if verify.status_code != 200:
            return None
        payload = verify.json()
        role = _normalize_role(payload.get("role"))
        return {
            "id": payload.get("user_id"),
            "role": role,
            "access_token": access_token,
            "refresh_token": tokens.get("refresh_token"),
        }


async def api_get_user(token: str, user_id: int) -> dict | None:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.get(f"/user-statistics/users/{user_id}", headers=_auth_headers(token))
        if resp.status_code != 200:
            return None
        return _normalize_user(resp.json())


async def api_get_user_admin(token: str, user_id: int) -> dict | None:
    """Админский запрос пользователя, использует защищенный /admin/users/{id}."""
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.get(
            f"/user-statistics/admin/users/{user_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code == 200:
            return _normalize_user(resp.json())

        # fallback: публичный профайл, если админский не сработал
        resp = await client.get(
            f"/user-statistics/users/{user_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return None
        return _normalize_user(resp.json())


async def api_get_all_users(token: str) -> list[dict]:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=20.0) as client:
        resp = await client.get(
            "/user-statistics/admin/users",
            params={"page": 1, "per_page": 200},
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        users = data.get("users", data if isinstance(data, list) else [])
        result: list[dict] = []
        for u in users:
            user_obj = _normalize_user(u)
            # В админском списке userStatistic нет роли — добираем из auth
            if user_obj.get("role") in (None, "student") and u.get("user_id"):
                auth_role = await _fetch_auth_role(client, token, u.get("user_id"))
                if auth_role:
                    user_obj["role"] = _normalize_role(auth_role)
            result.append(user_obj)
        return result


async def api_delete_user(token: str, user_id: int) -> bool:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.delete(
            f"/user-statistics/admin/users/{user_id}",
            headers=_auth_headers(token),
        )
        return resp.status_code == 200


async def api_register_user(
    token: str,
    name: str,
    surname: str,
    email: str,
    password: str,
    role: str,
    photo_path: str | None = None,
) -> dict | None:
    """
    Регистрация пользователя через userStatistic (создаёт auth запись), затем при необходимости повышаем роль.
    """
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=30.0) as client:
        # Если есть фото — используем публичную ручку регистрации с файлом
        if photo_path and os.path.isfile(photo_path):
            files = {"photo": (os.path.basename(photo_path), open(photo_path, "rb"), "image/jpeg")}
            data = {
                "first_name": name,
                "last_name": surname,
                "group_name": "N/A",
                "hse_email": email,
                "password": password,
            }
            resp = await client.post("/user-statistics/users/register", data=data, files=files)
        else:
            # Без фото — используем админский эндпоинт UserStatistic
            payload = {
                "first_name": name,
                "last_name": surname,
                "group_name": "N/A",
                "hse_email": email,
            }
            resp = await client.post(
                "/user-statistics/admin/users",
                json=payload,
                headers=_auth_headers(token),
            )

        if resp.status_code not in (200, 201):
            raise ValueError(f"user-statistics returned {resp.status_code}: {resp.text}")

        user = resp.json()
        user_id = user.get("user_id")

        # Создаём auth запись
        if user_id:
            role_for_auth = "admin" if role == "admin" else "user"
            auth_resp = await client.post(
                "/auth/create",
                json={"user_id": user_id, "password": password, "role": role_for_auth},
                headers=_auth_headers(token),
            )
            if auth_resp.status_code not in (200, 201):
                raise ValueError(f"auth/create returned {auth_resp.status_code}: {auth_resp.text}")

        # Повышение до admin через auth, если нужно
        if role == "admin" and user_id:
            await client.put(
                f"/auth/{user_id}",
                json={"role": "admin"},
                headers=_auth_headers(token),
            )

        return _normalize_user(user)


async def api_get_active_events(token: str) -> list[dict]:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.get(
            "/events/",
            params={"is_active_only": True, "limit": 100},
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return []
        payload = resp.json()
        events = payload.get("events", payload if isinstance(payload, list) else [])
        return [_normalize_event(ev) for ev in events]


async def api_get_all_events(token: str) -> list[dict]:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        # Сначала пытаемся админскую ручку (видит все события)
        resp = await client.get(
            "/events/admin/",
            params={"limit": 100, "include_inactive": True},
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            # fallback на пользовательский список (только активные)
            resp = await client.get(
                "/events/",
                params={"is_active_only": True, "limit": 100},
                headers=_auth_headers(token),
            )
        if resp.status_code != 200:
            return []
        payload = resp.json()
        events = payload.get("events", payload if isinstance(payload, list) else [])
        return [_normalize_event(ev) for ev in events]


async def api_get_event(token: str, event_id: int) -> dict | None:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.get(f"/events/{event_id}", headers=_auth_headers(token))
        if resp.status_code != 200:
            return None
        return _normalize_event(resp.json())


async def api_create_event(token: str, name: str, description: str, is_profile: bool, date: str) -> dict | None:
    payload = {
        "name": name,
        "opisanie": description,
        "profilnoe": is_profile,
        "date": date if "T" in date else f"{date}T00:00:00",
        "active": True,
    }
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.post(
            "/events/admin/",
            json=payload,
            headers=_auth_headers(token),
        )
        if resp.status_code not in (200, 201):
            return None
        return _normalize_event(resp.json())


async def api_deactivate_event(token: str, event_id: int) -> bool:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.put(
            f"/events/admin/{event_id}",
            json={"active": False},
            headers=_auth_headers(token),
        )
        return resp.status_code == 200


async def api_delete_event(token: str, event_id: int) -> bool:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.delete(f"/events/admin/{event_id}", headers=_auth_headers(token))
        return resp.status_code in (200, 204)


async def api_create_application(token: str, event_id: int, photo_path: str) -> dict | None:
    if not os.path.isfile(photo_path):
        return None

    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=30.0) as client:
        with open(photo_path, "rb") as f:
            files = {"photo": (os.path.basename(photo_path), f.read(), "image/jpeg")}

        resp = await client.post(
            "/attendances/",
            data={"event_id": str(event_id)},
            files=files,
            headers=_auth_headers(token),
        )
        if resp.status_code not in (200, 201):
            return None

        app = resp.json()
        ev = await api_get_event(token, event_id)
        return {
            "id": app.get("attendance_id"),
            "status": app.get("status"),
            "event_id": event_id,
            "user_id": app.get("user_id"),
            "event_name": ev.get("name") if ev else "",
            "photo_path": app.get("file_path"),
            "created_at": app.get("created_at"),
        }


async def api_get_my_applications(token: str) -> list[dict]:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.get("/attendances/", headers=_auth_headers(token))
        if resp.status_code != 200:
            return []
        payload = resp.json()
        apps = payload.get("attendances", payload if isinstance(payload, list) else [])

    result = []
    for app in apps:
        ev = await api_get_event(token, app.get("event_id"))
        result.append(
            {
                "id": app.get("attendance_id"),
                "status": app.get("status"),
                "event_id": app.get("event_id"),
                "user_id": app.get("user_id"),
                "event_name": (ev.get("name") if ev else "") or f"Мероприятие #{app.get('event_id')}",
                "photo_path": app.get("file_path"),
                "created_at": app.get("created_at"),
            }
        )
    return result


async def api_get_all_applications(token: str) -> list[dict]:
    """
    Админ: получаем заявки в ожидании (других эндпоинтов в сервисе нет).
    """
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=15.0) as client:
        resp = await client.get("/attendances/admin/pending", headers=_auth_headers(token))
        if resp.status_code != 200:
            return []
        payload = resp.json()
        apps = payload.get("attendances", payload if isinstance(payload, list) else [])

    result = []
    for app in apps:
        ev = await api_get_event(token, app.get("event_id"))
        result.append(
            {
                "id": app.get("attendance_id"),
                "status": app.get("status"),
                "event_id": app.get("event_id"),
                "user_id": app.get("user_id"),
                "event_name": ev.get("name") if ev else "",
                "photo_path": app.get("file_path"),
                "created_at": app.get("created_at"),
            }
        )
    return result


async def api_approve_application(token: str, app_id: int) -> bool:
    ev_points = 0
    # Пытаемся вычислить баллы
    app = await api_get_application(token, app_id)
    if app:
        ev = await api_get_event(token, app.get("event_id"))
        if ev:
            base = 2
            mult = 1.5 if ev.get("is_profile") else 0.5
            ev_points = int(base * mult)

    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.post(
            f"/attendances/admin/review/{app_id}",
            json={"approve": True, "points": ev_points or None},
            headers=_auth_headers(token),
        )
        return resp.status_code == 200


async def api_reject_application(token: str, app_id: int) -> bool:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.post(
            f"/attendances/admin/review/{app_id}",
            json={"approve": False},
            headers=_auth_headers(token),
        )
        return resp.status_code == 200


async def api_get_application(token: str, app_id: int) -> dict | None:
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.get(
            f"/attendances/admin/detail/{app_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return None
        app = resp.json()

    ev = await api_get_event(token, app.get("event_id"))
    return {
        "id": app.get("attendance_id"),
        "status": app.get("status"),
        "event_id": app.get("event_id"),
        "user_id": app.get("user_id"),
        "event_name": ev.get("name") if ev else "",
        "photo_path": app.get("attendance_photo_url") or app.get("file_path"),
        "created_at": app.get("created_at"),
    }
