import os
import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _normalize_application(app: dict, event_name: str | None = None) -> dict:
    photo_path = app.get("file_path") or app.get("photo_path")
    return {
        "id": app.get("attendance_id") or app.get("id"),
        "event_id": app.get("event_id"),
        "user_id": app.get("user_id"),
        "status": app.get("status"),
        "created_at": app.get("created_at"),
        "photo_path": photo_path,
        "photo_url": f"/static/{photo_path}" if photo_path else None,
        "is_aproved": app.get("is_aproved"),
        "notes": app.get("notes"),
        "event_name": event_name,
    }


async def _get_event_name(token: str, event_id: int | str) -> str | None:
    try:
        async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
            resp = await client.get(f"/events/{event_id}", headers=_auth_headers(token))
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("name")
    except Exception:
        return None


async def api_create_application(token: str, event_id: int, photo_path: str, notes: str | None = None) -> dict | None:
    """
    Создать заявку через /attendances/.
    """
    if not os.path.isfile(photo_path):
        return None

    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        with open(photo_path, "rb") as f:
            files = {"photo": ("photo.jpg", f.read(), "image/jpeg")}
        data = {"event_id": str(event_id)}
        if notes:
            data["notes"] = notes

        resp = await client.post(
            "/attendances/",
            data=data,
            files=files,
            headers=_auth_headers(token),
        )

        if resp.status_code not in (200, 201):
            return None

        event_name = await _get_event_name(token, event_id)
        return _normalize_application(resp.json(), event_name)


async def api_get_my_applications(token: str) -> list[dict]:
    """
    Получить заявки текущего пользователя (используется токен).
    """
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.get("/attendances/", headers=_auth_headers(token))
        if resp.status_code != 200:
            return []

        payload = resp.json()
        apps = payload.get("attendances", payload if isinstance(payload, list) else [])

    result = []
    for app in apps:
        event_name = await _get_event_name(token, app.get("event_id"))
        result.append(_normalize_application(app, event_name))
    return result


async def api_get_pending_applications(token: str) -> list[dict]:
    """Получить заявки в ожидании для админа."""
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.get("/attendances/admin/pending", headers=_auth_headers(token))
        if resp.status_code != 200:
            return []

        payload = resp.json()
        apps = payload.get("attendances", payload if isinstance(payload, list) else [])

    result = []
    for app in apps:
        event_name = await _get_event_name(token, app.get("event_id"))
        result.append(_normalize_application(app, event_name))
    return result


async def api_get_application(token: str, app_id: int | str) -> dict | None:
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.get(
            f"/attendances/admin/detail/{app_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    event_name = await _get_event_name(token, data.get("event_id"))
    return _normalize_application(data, event_name)


async def api_approve_application(token: str, app_id: int | str, notes: str | None = None, points: float | None = None) -> bool:
    """
    Одобрить заявку.
    """
    payload: dict[str, str | float | bool | None] = {"approve": True}
    if notes:
        payload["notes"] = notes
    if points is not None:
        payload["points"] = points

    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.post(
            f"/attendances/admin/review/{app_id}",
            json=payload,
            headers=_auth_headers(token),
        )
        return resp.status_code == 200


async def api_reject_application(token: str, app_id: int | str, notes: str | None = None) -> bool:
    payload: dict[str, str | bool] = {"approve": False}
    if notes:
        payload["notes"] = notes

    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.post(
            f"/attendances/admin/review/{app_id}",
            json=payload,
            headers=_auth_headers(token),
        )
        return resp.status_code == 200
