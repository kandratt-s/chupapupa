import os
import re
import asyncio
import hashlib
from email_validator import validate_email, EmailNotValidError
from aiogram import types

from services.bot.gateway_bot.config import PHOTOS_DIR


# ================================================================
# ВАЛИДАЦИЯ EMAIL
# ================================================================
def validate_mail(email: str) -> str | None:
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError:
        return None


# ================================================================
# ВАЛИДАЦИЯ ПАРОЛЯ
# ================================================================
def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not (re.search(r"[A-Z]", password) or re.search(r"[a-z]", password)):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True


# ================================================================
# ХЕШИРОВАНИЕ ПАРОЛЯ (если понадобится)
# ================================================================
def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


# ================================================================
# ДИРЕКТОРИЯ ДЛЯ ФОТО
# ================================================================
def ensure_photos_dir():
    os.makedirs(PHOTOS_DIR, exist_ok=True)


# ================================================================
# БЕЗОПАСНОЕ УДАЛЕНИЕ СООБЩЕНИЯ
# ================================================================
async def delete_message_safe(chat_id: int, message_id: int, bot=None):
    if not bot:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        await asyncio.sleep(0.1)
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass


# ================================================================
# СКАЧИВАНИЕ ФОТО ИЗ TELEGRAM
# ================================================================
async def download_telegram_photo(message: types.Message, base_dir: str) -> str:
    """
    Скачивает фото из Telegram в локальную директорию.
    Возвращает путь к локальному файлу.
    """
    ensure_photos_dir()

    photo = message.photo[-1]
    file_id = photo.file_id

    filename = f"{message.from_user.id}_{int(message.date.timestamp())}.jpg"
    path = os.path.join(base_dir, filename)

    try:
        file_obj = await message.bot.get_file(file_id)
        url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        )

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(path, "wb") as f_out:
                f_out.write(resp.content)

    except Exception:
        # fallback
        try:
            await photo.download(destination_file=path)
        except Exception:
            raise RuntimeError("Не удалось скачать фото")

    return path


# ================================================================
# ПРОСТОЙ ЛОГ ОШИБОК
# ================================================================
def safe_log_error(context: str, exc: Exception) -> None:
    print(f"[ERROR] {context}: {exc}")
