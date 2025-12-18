import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


async def api_login(email: str, password: str, telegram_id: str | None = None) -> dict | None:
    """
    Логин через API Gateway -> Auth service.
    Возвращает словарь с access/refresh токенами, user_id и role либо None при ошибке.
    """
    payload = {"email": email, "password": password}
    if telegram_id:
        # для аудита можно передать в метаданные (бэкенд пока игнорирует)
        payload["telegram_id"] = telegram_id

    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.post("/auth/login-email", json=payload)
        if resp.status_code != 200:
            return None

        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None

        verify = await client.get(
            "/auth/verify-token", headers={"Authorization": f"Bearer {access_token}"}
        )
        if verify.status_code != 200:
            return None

        payload = verify.json()

        return {
            "access_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "bearer"),
            "expires_in": token_data.get("expires_in"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role", "user"),
        }
