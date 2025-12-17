"""
Сервис для проксирования запросов к микросервисам.
"""

import logging
from typing import Optional

import httpx
from app.core.config import settings
from fastapi import HTTPException, Request, Response, status

logger = logging.getLogger(__name__)


class ProxyService:
    """Сервис для проксирования запросов к микросервисам"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT)

    async def close(self) -> None:
        """Закрыть HTTP клиент"""
        await self.http_client.aclose()

    def is_public_endpoint(self, path: str) -> bool:
        """Проверяет, является ли эндпоинт публичным"""
        return any(
            path.startswith(endpoint) or path == endpoint.rstrip("/")
            for endpoint in settings.PUBLIC_ENDPOINTS
        )

    def get_service_url(self, path: str) -> Optional[str]:
        """Определяет URL микросервиса по пути запроса"""
        for route_prefix, service_url in settings.SERVICE_ROUTES.items():
            if path.startswith(route_prefix):
                return service_url
        return None

    async def validate_auth_headers(self, request: Request) -> bool:
        """Валидация заголовков аутентификации через auth сервис"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False

        try:
            response = await self.http_client.get(
                f"{settings.AUTH_SERVICE_URL}/auth/verify-token",
                headers={"Authorization": auth_header},
                timeout=settings.AUTH_TIMEOUT,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Auth validation failed: {e}")
            return False

    def _prepare_service_path(self, path: str) -> str:
        """Подготавливает путь для отправки в микросервис"""
        service_path = path
        
        # Специальная обработка для attendance admin endpoints
        if path.startswith("/attendances/admin"):
            return path.replace("/attendances", "")
        
        # Специальная обработка для static файлов - оставляем полный путь
        if path.startswith("/static/"):
            return path
            
        # Для остальных attendance endpoints оставляем полный путь
        if path.startswith("/attendances"):
            return path
            
        # Для остальных сервисов убираем префикс
        for route_prefix in settings.SERVICE_ROUTES.keys():
            if path.startswith(route_prefix):
                service_path = path[len(route_prefix) :]
                break

        if not service_path or service_path == "/":
            service_path = ""

        return service_path

    def _prepare_headers(self, request: Request) -> dict[str, str]:
        """Подготавливает заголовки для отправки в микросервис"""
        headers = dict(request.headers)
        excluded_headers = ["host", "connection", "upgrade", "proxy-connection"]
        for header in excluded_headers:
            headers.pop(header, None)
        return headers

    def _prepare_response_headers(self, response: httpx.Response) -> dict[str, str]:
        """Подготавливает заголовки ответа от микросервиса"""
        response_headers = dict(response.headers)
        excluded_response_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        for header in excluded_response_headers:
            response_headers.pop(header, None)
        return response_headers

    async def forward_request(
        self,
        request: Request,
        service_url: str,
        path: str,
    ) -> Response:
        """Пересылает запрос в соответствующий микросервис"""
        try:
            # Подготовка URL для микросервиса
            service_path = self._prepare_service_path(path)
            target_url = f"{service_url}{service_path}"

            # Подготовка заголовков
            headers = self._prepare_headers(request)

            # Подготовка тела запроса - используем stream для multipart/form-data
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                # Читаем тело как поток байтов для корректной обработки multipart
                body_bytes = b""
                async for chunk in request.stream():
                    body_bytes += chunk
                body = body_bytes if body_bytes else None

            logger.debug(f"📤 Forwarding {request.method} {path} -> {target_url}")

            # Выполнение запроса к микросервису
            response = await self.http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

            # Подготовка ответа
            response_headers = self._prepare_response_headers(response)

            logger.debug(f"📥 Response from {target_url}: {response.status_code}")

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )

        except httpx.RequestError as e:
            logger.error(f"❌ Request error to {service_url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {str(e)}",
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error forwarding to {service_url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gateway error: {str(e)}",
            )

    async def check_service_health(self, service_url: str) -> str:
        """Проверяет здоровье микросервиса"""
        try:
            response = await self.http_client.get(
                f"{service_url}/health", timeout=settings.HEALTH_CHECK_TIMEOUT
            )
            return "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            return "unavailable"


# Глобальный экземпляр сервиса проксирования
proxy_service = ProxyService()