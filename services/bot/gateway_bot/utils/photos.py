import os
import httpx
from aiogram import types
from services.bot.gateway_bot.config import PHOTOS_DIR


async def download_telegram_photo(
    message: types.Message, base_dir: str = PHOTOS_DIR
) -> str:
    """
    Скачивает фото из Telegram в локальную директорию.
    Возвращает путь к локальному файлу.
    """

    os.makedirs(base_dir, exist_ok=True)

    photo = message.photo[-1]
    file_id = photo.file_id

    filename = f"{message.from_user.id}_{int(message.date.timestamp())}.jpg"
    path = os.path.join(base_dir, filename)

    try:
        # Получаем путь к файлу в Telegram
        file_obj = await message.bot.get_file(file_id)
        url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        )

        # Скачиваем
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()

            with open(path, "wb") as f_out:
                f_out.write(resp.content)

    except Exception:
        # fallback — если Telegram API не дал прямой путь
        try:
            await photo.download(destination_file=path)
        except Exception as e:
            raise RuntimeError(f"Не удалось скачать фото: {e}")

    return path
