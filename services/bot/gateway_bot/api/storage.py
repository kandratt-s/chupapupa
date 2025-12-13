import httpx
from services.bot.gateway_bot.config import API_GATEWAY_URL, TIMEOUT


async def api_upload_photo(token: str, local_path: str):
    """
    Загружает фото в Storage Service через API Gateway.
    Возвращает JSON вида:
    {
        "url": "https://storage/.../photo.jpg"
    }
    """

    with open(local_path, "rb") as f:
        file_bytes = f.read()

    async with httpx.AsyncClient(base_url=API_GATEWAY_URL, timeout=TIMEOUT) as client:
        resp = await client.post(
            "/storage/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("photo.jpg", file_bytes, "image/jpeg")},
        )

        if resp.status_code != 200:
            return None

        return resp.json()
