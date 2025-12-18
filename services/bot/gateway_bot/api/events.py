import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _normalize_event(ev: dict) -> dict:
    """Привести ответ Event сервиса к виду, ожидаемому ботом."""
    return {
        "id": ev.get("event_id") or ev.get("id"),
        "name": ev.get("name"),
        "date": ev.get("date"),
        "description": ev.get("opisanie") or ev.get("description"),
        "is_profile": ev.get("profilnoe") or ev.get("is_profile") or False,
        "is_active": ev.get("active", True),
    }


async def api_get_events(token: str) -> list[dict]:
    """Получить активные события."""
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
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


async def api_get_event(token: str, event_id: int | str) -> dict | None:
    """Получить одно событие."""
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.get(f"/events/{event_id}", headers=_auth_headers(token))
        if resp.status_code != 200:
            return None

        return _normalize_event(resp.json())
