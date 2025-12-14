"""
Pydantic схемы для API Gateway CHUPAPUPA v2.0
"""

from typing import Any, Dict

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Модель ответа для health check"""

    service: str
    status: str
    version: str
    environment: str
    services: Dict[str, str]
    timestamp: float


class ServiceStats(BaseModel):
    """Статистика работы Gateway"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float


class ServiceInfo(BaseModel):
    """Информация о сервисе"""

    service: str
    version: str
    description: str
    environment: str
    docs: str
    health: str
    stats: str
    available_services: list[str]


class RoutesInfo(BaseModel):
    """Информация о доступных маршрутах"""

    available_routes: Dict[str, str]
    description: str
    usage: str
    public_endpoints: list[str]


class ErrorResponse(BaseModel):
    """Модель ответа при ошибке"""

    error: str
    message: str
    detail: str | None = None
    timestamp: float


class ProxyRequest(BaseModel):
    """Модель запроса для проксирования"""

    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: bytes | None = None


class ProxyResponse(BaseModel):
    """Модель ответа от проксированного сервиса"""

    status_code: int
    headers: Dict[str, str]
    content: bytes
    media_type: str | None = None
    process_time: float