"""
Основные API роутеры для Gateway.
"""

import time
from typing import Any, Dict

from app.core.config import settings
from app.schemas import HealthResponse, RoutesInfo, ServiceInfo, ServiceStats
from app.services.proxy import proxy_service
from app.services.stats import stats_service
from fastapi import APIRouter

router = APIRouter()


@router.get("/", response_model=ServiceInfo)
async def root() -> ServiceInfo:
    """Корневой endpoint Gateway"""
    return ServiceInfo(
        service="CHUPAPUPA API Gateway",
        version="2.0.0",
        description="Центральная точка доступа ко всем микросервисам системы",
        environment=settings.ENVIRONMENT,
        docs="/docs",
        health="/health",
        stats="/stats",
        available_services=list(settings.SERVICE_ROUTES.keys()),
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверка здоровья Gateway и всех микросервисов"""
    services_health = {}

    for route_prefix, service_url in settings.SERVICE_ROUTES.items():
        services_health[route_prefix] = await proxy_service.check_service_health(service_url)

    # Основные активные сервисы (исключаем admin, bot, web)
    active_services = ["/auth", "/events", "/attendance", "/user-statistics"]
    active_services_health = [
        services_health.get(service, "unavailable") 
        for service in active_services
    ]
    
    overall_status = (
        "healthy" if all(status == "healthy" for status in active_services_health) else "degraded"
    )

    return HealthResponse(
        service="api-gateway",
        status=overall_status,
        version="2.0.0",
        environment=settings.ENVIRONMENT,
        services=services_health,
        timestamp=time.time(),
    )


@router.get("/stats", response_model=ServiceStats)
async def get_stats() -> ServiceStats:
    """Получение статистики работы Gateway"""
    stats = stats_service.get_stats()

    return ServiceStats(
        total_requests=stats["total_requests"],
        successful_requests=stats["successful_requests"],
        failed_requests=stats["failed_requests"],
        average_response_time=stats["average_response_time"],
    )


@router.get("/routes", response_model=RoutesInfo)
async def get_routes() -> RoutesInfo:
    """Показать доступные маршруты"""
    return RoutesInfo(
        available_routes=settings.SERVICE_ROUTES,
        description="Маппинг маршрутов на микросервисы",
        usage="Отправляйте запросы на /auth/*, /events/*, /attendance/*, etc.",
        public_endpoints=settings.PUBLIC_ENDPOINTS,
    )


@router.post("/stats/reset")
async def reset_stats() -> Dict[str, Any]:
    """Сброс статистики (только для разработки)"""
    if settings.ENVIRONMENT != "development":
        return {"error": "Statistics reset is only available in development mode"}

    stats_service.reset_stats()
    return {"message": "Statistics reset successfully"}