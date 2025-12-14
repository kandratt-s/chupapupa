"""
Сервис для работы с файлами (фотографии, PDF)
"""

import io
import os
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
from fastapi import HTTPException, UploadFile
from PIL import Image


class PhotoService:
    """Сервис для управления файлами (фотографии, документы)"""

    def __init__(self, photos_dir: str = "photos"):
        self.photos_dir = Path(photos_dir)
        self.users_dir = self.photos_dir / "users"
        self.attendances_dir = self.photos_dir / "attendances"

        # Создаем директории если их нет
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.attendances_dir.mkdir(parents=True, exist_ok=True)

    async def save_attendance_photo(self, photo: UploadFile, attendance_id: int) -> str:
        """Сохранить файл с мероприятия (фото или PDF)"""

        # Разрешенные типы файлов
        allowed_types = {
            # Изображения
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/webp": ".webp",
            "image/tiff": ".tiff",
            "image/tif": ".tiff",
            # PDF документы
            "application/pdf": ".pdf",
            # Дополнительные форматы изображений
            "image/svg+xml": ".svg",
            "image/x-icon": ".ico",
        }

        # Проверяем тип файла
        if not photo.content_type or photo.content_type not in allowed_types:
            allowed_formats = ", ".join(set(allowed_types.values()))
            raise HTTPException(
                status_code=400, detail=f"Неподдерживаемый тип файла. Разрешены: {allowed_formats}"
            )

        # Читаем содержимое файла
        contents = await photo.read()

        # Проверяем размер файла (максимум 20MB для PDF, 10MB для изображений)
        max_size = 20 * 1024 * 1024 if photo.content_type == "application/pdf" else 10 * 1024 * 1024
        if len(contents) > max_size:
            max_mb = 20 if photo.content_type == "application/pdf" else 10
            raise HTTPException(
                status_code=400, detail=f"Файл слишком большой (максимум {max_mb}MB)"
            )

        # Валидируем содержимое файла
        await self._validate_file_content(contents, photo.content_type)

        # Определяем расширение файла
        file_extension = self._get_file_extension(photo.filename, photo.content_type, allowed_types)

        # Создаем путь для сохранения
        filename = f"{attendance_id}{file_extension}"
        file_path = self.attendances_dir / filename

        # Сохраняем файл
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(contents)
        except Exception:
            raise HTTPException(status_code=500, detail="Ошибка при сохранении файла") from None

        # Возвращаем относительный путь
        return f"photos/attendances/{filename}"

    def get_user_photo_path(self, user_id: int) -> str:
        """Получить путь к файлу пользователя (фото или PDF)"""
        # Проверяем существующие расширения (приоритет фото)
        extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".tiff",
            ".svg",
            ".ico",
            ".pdf",
        ]

        for ext in extensions:
            file_path = self.users_dir / f"{user_id}{ext}"
            if file_path.exists():
                return f"photos/users/{user_id}{ext}"

        # Если не найдено, возвращаем путь с .jpg по умолчанию
        return f"photos/users/{user_id}.jpg"

    def _get_file_extension(
        self, filename: str | None, content_type: str, allowed_types: dict[str, str]
    ) -> str:
        """Определить расширение файла"""

        # Сначала пробуем получить из имени файла
        if filename:
            _, ext = os.path.splitext(filename)
            ext_lower = ext.lower()
            # Проверяем, что расширение из filename соответствует разрешенным
            if ext_lower in allowed_types.values():
                return ext_lower

        # Если не получилось, определяем по content_type
        return str(allowed_types.get(content_type, ".jpg"))

    async def _validate_file_content(self, contents: bytes, content_type: str) -> None:
        """Валидация содержимого файла"""

        if content_type == "application/pdf":
            # Простая проверка PDF (начинается с %PDF-)
            if not contents.startswith(b"%PDF-"):
                raise HTTPException(status_code=400, detail="Некорректный PDF файл")

        elif content_type.startswith("image/"):
            # Проверяем изображение с помощью PIL
            try:
                image = Image.open(io.BytesIO(contents))
                # Проверяем, что изображение можно открыть
                image.verify()
            except Exception:
                raise HTTPException(
                    status_code=400, detail="Некорректный файл изображения"
                ) from None

        else:
            # Для других типов файлов базовая проверка
            if len(contents) == 0:
                raise HTTPException(status_code=400, detail="Пустой файл")

    def get_photo_url(self, photo_path: str | None) -> str | None:
        """Получить URL файла"""
        if not photo_path:
            return None
        return f"/static/{photo_path}"

    async def delete_photo(self, photo_path: str) -> bool:
        """Удалить файл"""
        try:
            file_path = Path(photo_path)
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception:
            pass
        return False
