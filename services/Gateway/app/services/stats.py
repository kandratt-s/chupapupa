"""
Сервис для сбора и управления статистикой запросов в API Gateway.
"""

import time
from typing import Dict


class StatsService:
    """Сервис для сбора статистики запросов"""

    def __init__(self):
        self._stats: Dict[str, float | int] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
        }

    def increment_total_requests(self) -> None:
        """Увеличить счетчик общих запросов"""
        self._stats["total_requests"] += 1

    def increment_successful_requests(self) -> None:
        """Увеличить счетчик успешных запросов"""
        self._stats["successful_requests"] += 1

    def increment_failed_requests(self) -> None:
        """Увеличить счетчик неуспешных запросов"""
        self._stats["failed_requests"] += 1

    def add_response_time(self, response_time: float) -> None:
        """Добавить время ответа в статистику"""
        self._stats["total_response_time"] += response_time

    def get_average_response_time(self) -> float:
        """Получить среднее время ответа"""
        total_requests = self._stats["total_requests"]
        if total_requests == 0:
            return 0.0
        return round(self._stats["total_response_time"] / total_requests, 3)

    def get_stats(self) -> Dict[str, int | float]:
        """Получить всю статистику"""
        return {
            "total_requests": int(self._stats["total_requests"]),
            "successful_requests": int(self._stats["successful_requests"]),
            "failed_requests": int(self._stats["failed_requests"]),
            "average_response_time": self.get_average_response_time(),
        }

    def reset_stats(self) -> None:
        """Сброс всей статистики"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
        }


# Глобальный экземпляр сервиса статистики
stats_service = StatsService()