"""
UserStatistic service models.
Переадресация импортов на правильные модели в app/models.py
"""

from app.models import User

# Экспортируем модели для обратной совместимости
__all__ = ["User"]
