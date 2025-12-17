"""
Роутер для проксирования запросов к микросервисам.
"""

import logging

from app.core.config import settings
from app.services.proxy import proxy_service
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def gateway_proxy(request: Request, path: str) -> Response:
    """Основной proxy endpoint для пересылки запросов в микросервисы"""

    full_path = f"/{path}"

    # Проверка аутентификации для приватных эндпоинтов
    if not proxy_service.is_public_endpoint(full_path):
        auth_valid = await proxy_service.validate_auth_headers(request)
        if not auth_valid:
            logger.warning(f"🚫 Unauthorized access attempt to {full_path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized. Valid token required."},
            )

    # Получение URL микросервиса
    service_url = proxy_service.get_service_url(full_path)

    if not service_url:
        logger.warning(f"⚠️  No service found for path: {full_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"No service found for path: {full_path}",
                "available_routes": list(settings.SERVICE_ROUTES.keys()),
                "hint": "Check /routes endpoint for available routes",
            },
        )

    return await proxy_service.forward_request(request, service_url, full_path)