"""
Сервис для работы с фотографиями пользователей
"""

import io
import os
from pathlib import Path
from typing import Optional

import aiofiles  # type: ignore[import-untyped]
from fastapi import HTTPException, UploadFile
from PIL import Image


class PhotoService:
    """Сервис для управления фотографиями пользователей"""

    def __init__(self, photos_dir: str = "/shared/photos"):
        self.photos_dir = Path(photos_dir)
        self.faces_dir = self.photos_dir / "faces"

        # Создаем директории если их нет
        self.faces_dir.mkdir(parents=True, exist_ok=True)

    async def save_user_photo(self, photo: UploadFile, user_id: int) -> str:
        """Сохранить фотографию пользователя"""

        # Разрешенные типы файлов
        allowed_types = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg", 
            "image/png": ".png",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/webp": ".webp",
            "image/tiff": ".tiff",
            "image/tif": ".tiff",
        }

        # Проверяем тип файла
        if not photo.content_type or photo.content_type not in allowed_types:
            allowed_formats = ", ".join(set(allowed_types.values()))
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый тип файла. Разрешены только: {allowed_formats}",
            )

        # Получаем расширение файла
        file_extension = allowed_types[photo.content_type]
        
        # Создаем имя файла на основе user_id
        filename = f"{user_id}{file_extension}"
        file_path = self.faces_dir / filename

        try:
            # Читаем содержимое файла
            content = await photo.read()
            
            # Проверяем, что это действительно изображение
            try:
                image = Image.open(io.BytesIO(content))
                image.verify()  # Проверяем целостность изображения
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Файл поврежден или не является изображением"
                )

            # Сохраняем файл асинхронно
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            return str(file_path)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при сохранении файла: {str(e)}"
            )

    async def get_user_photo_path(self, user_id: int) -> Optional[str]:
        """Получить путь к фотографии пользователя"""
        
        # Ищем файл с любым из поддерживаемых расширений
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"]
        
        for ext in extensions:
            file_path = self.faces_dir / f"{user_id}{ext}"
            if file_path.exists():
                return str(file_path)
        
        return None

    async def delete_user_photo(self, user_id: int) -> bool:
        """Удалить фотографию пользователя"""
        
        photo_path = await self.get_user_photo_path(user_id)
        if photo_path:
            try:
                os.remove(photo_path)
                return True
            except Exception:
                return False
        return False

    def get_photo_url(self, user_id: int) -> Optional[str]:
        """Получить URL фотографии пользователя для отдачи через API"""
        
        # Проверяем существование файла синхронно для быстрого ответа
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"]
        
        for ext in extensions:
            file_path = self.faces_dir / f"{user_id}{ext}"
            if file_path.exists():
                return f"/static/faces/{user_id}{ext}"
        
        return None

    async def update_user_photo(self, photo: UploadFile, user_id: int) -> str:
        """Обновить фотографию пользователя (удаляет старую и сохраняет новую)"""
        
        # Удаляем существующую фотографию
        await self.delete_user_photo(user_id)
        
        # Сохраняем новую
        return await self.save_user_photo(photo, user_id)

    def list_all_photos(self) -> list[str]:
        """Получить список всех фотографий пользователей"""
        
        photos = []
        if self.faces_dir.exists():
            for file_path in self.faces_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in [
                    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"
                ]:
                    photos.append(file_path.name)
        return photos