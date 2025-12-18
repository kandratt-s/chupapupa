import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def api_get_user(token: str, user_id: int | str) -> dict | None:
    """
    Получить пользователя из userStatistic сервиса через Gateway.
    """
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.get(
            f"/user-statistics/users/{user_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        # Приводим ключи к ожидаемым в боте
        return {
            "user_id": data.get("user_id"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("hse_email"),
            "practice_points": data.get("practice_points", 0),
            "photo_url": data.get("photo_url") or data.get("photo_path"),
        }
