import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def api_add_points(token: str, user_id: int | str, points: float) -> bool:
    """
    Добавить баллы пользователю (админ).
    """
    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.patch(
            f"/user-statistics/admin/user/{user_id}/add-points",
            json={"points": points, "reason": "added via bot"},
            headers=_auth_headers(token),
        )
        return resp.status_code == 200
