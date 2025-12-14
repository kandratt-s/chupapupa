"""
CHUPAPUPA API Gateway v2.0 - Production Ready
Центральная точка доступа ко всем микросервисам системы.
Обеспечивает маршрутизацию, аутентификацию, логирование и мониторинг.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Settings:
    """Конфигурация из переменных окружения"""

    # Основные настройки
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()

    # Настройки сервера
    HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
    PORT = int(os.getenv("GATEWAY_PORT", "8000"))

    # URL микросервисов (внутренние адреса)
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8000")
    ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://attendance-service:8003")
    USER_STATISTIC_SERVICE_URL = os.getenv("USER_STATISTIC_SERVICE_URL", "http://user-statistic-service:8000")
    ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin-service:8000")
    BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot-service:8000")
    WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

    # Security
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"


settings = Settings()

# Конфигурация логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api-gateway")

# Создание приложения
app = FastAPI(
    title="CHUPAPUPA API Gateway v2.0",
    description="Центральная точка доступа ко всем микросервисам системы CHUPAPUPA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маппинг маршрутов на микросервисы
SERVICE_ROUTES = {
    "/auth": settings.AUTH_SERVICE_URL,
    "/api/auth": settings.AUTH_SERVICE_URL,
    "/events": settings.EVENT_SERVICE_URL,
    "/api/events": settings.EVENT_SERVICE_URL,
    "/attendance": settings.ATTENDANCE_SERVICE_URL,
    "/api/attendance": settings.ATTENDANCE_SERVICE_URL,
    "/user-statistics": settings.USER_STATISTIC_SERVICE_URL,
    "/api/user-statistics": settings.USER_STATISTIC_SERVICE_URL,
    "/admin": settings.ADMIN_SERVICE_URL,
    "/api/admin": settings.ADMIN_SERVICE_URL,
    "/bot": settings.BOT_SERVICE_URL,
    "/api/bot": settings.BOT_SERVICE_URL,
    "/web": settings.WEB_SERVICE_URL,
    "/api/web": settings.WEB_SERVICE_URL,
}

# Публичные эндпоинты (не требуют аутентификации)
PUBLIC_ENDPOINTS = {
    "/health",
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/",
    "/routes",
    "/stats",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
}

# HTTP клиент для запросов к микросервисам
http_client = httpx.AsyncClient(timeout=30.0)


class HealthResponse(BaseModel):
    """Модель ответа для health check"""

    service: str
    status: str
    version: str
    environment: str
    services: Dict[str, str]
    timestamp: float


class ServiceStats(BaseModel):
    """Статистика сервисов"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float


# Статистика запросов
request_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_response_time": 0.0,
}


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    """Middleware для логирования и подсчета статистики"""
    start_time = time.time()
    request_stats["total_requests"] += 1

    # Логирование входящего запроса
    logger.info(f"🔵 {request.method} {request.url} - Client: {request.client.host if request.client else 'unknown'}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Обновление статистики
        request_stats["total_response_time"] += process_time
        if response.status_code < 400:
            request_stats["successful_requests"] += 1
        else:
            request_stats["failed_requests"] += 1

        # Логирование ответа
        status_color = "🟢" if response.status_code < 400 else "🔴"
        logger.info(f"{status_color} {request.method} {request.url} - {response.status_code} - {process_time:.3f}s")

        response.headers["X-Process-Time"] = str(process_time)
        return response

    except Exception as e:
        process_time = time.time() - start_time
        request_stats["failed_requests"] += 1

        logger.error(f"🔴 {request.method} {request.url} - ERROR: {str(e)} - {process_time:.3f}s")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Gateway Error", "message": str(e)},
        )


def is_public_endpoint(path: str) -> bool:
    """Проверяет, является ли эндпоинт публичным"""
    return any(path.startswith(endpoint) or path == endpoint.rstrip("/") 
              for endpoint in PUBLIC_ENDPOINTS)


def get_service_url(path: str) -> Optional[str]:
    """Определяет URL микросервиса по пути запроса"""
    for route_prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(route_prefix):
            return service_url
    return None


async def validate_auth_headers(request: Request) -> bool:
    """Валидация заголовков аутентификации через auth сервис"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return False
    
    try:
        response = await http_client.get(
            f"{settings.AUTH_SERVICE_URL}/verify-token",
            headers={"Authorization": auth_header},
            timeout=5.0
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Auth validation failed: {e}")
        return False


async def forward_request(
    request: Request,
    service_url: str,
    path: str,
) -> Response:
    """Пересылает запрос в соответствующий микросервис"""
    try:
        # Подготовка URL для микросервиса
        service_path = path
        for route_prefix in SERVICE_ROUTES.keys():
            if path.startswith(route_prefix):
                service_path = path[len(route_prefix):]
                break

        if not service_path or service_path == "/":
            service_path = ""

        target_url = f"{service_url}{service_path}"

        # Копирование заголовков (исключая hop-by-hop заголовки)
        headers = dict(request.headers)
        excluded_headers = ["host", "connection", "upgrade", "proxy-connection"]
        for header in excluded_headers:
            headers.pop(header, None)

        # Получение тела запроса
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

        logger.debug(f"📤 Forwarding {request.method} {path} -> {target_url}")

        # Выполнение запроса к микросервису
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )

        # Копирование заголовков ответа
        response_headers = dict(response.headers)
        excluded_response_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        for header in excluded_response_headers:
            response_headers.pop(header, None)

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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверка здоровья Gateway и всех микросервисов"""
    services_health = {}

    for route_prefix, service_url in SERVICE_ROUTES.items():
        try:
            response = await http_client.get(f"{service_url}/health", timeout=5.0)
            services_health[route_prefix] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services_health[route_prefix] = "unavailable"

    overall_status = "healthy" if all(status == "healthy" for status in services_health.values()) else "degraded"

    return HealthResponse(
        service="api-gateway",
        status=overall_status,
        version="2.0.0",
        environment=settings.ENVIRONMENT,
        services=services_health,
        timestamp=time.time(),
    )


@app.get("/stats", response_model=ServiceStats)
async def get_stats() -> ServiceStats:
    """Получение статистики работы Gateway"""
    avg_response_time = (
        request_stats["total_response_time"] / request_stats["total_requests"]
        if request_stats["total_requests"] > 0
        else 0.0
    )

    return ServiceStats(
        total_requests=request_stats["total_requests"],
        successful_requests=request_stats["successful_requests"],
        failed_requests=request_stats["failed_requests"],
        average_response_time=round(avg_response_time, 3),
    )


@app.get("/")
async def root() -> Dict[str, Any]:
    """Корневой endpoint Gateway"""
    return {
        "service": "CHUPAPUPA API Gateway",
        "version": "2.0.0",
        "description": "Центральная точка доступа ко всем микросервисам системы",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "stats": "/stats",
        "available_services": list(SERVICE_ROUTES.keys()),
    }


@app.get("/routes")
async def get_routes() -> Dict[str, Any]:
    """Показать доступные маршруты"""
    return {
        "available_routes": SERVICE_ROUTES,
        "description": "Маппинг маршрутов на микросервисы",
        "usage": "Отправляйте запросы на /auth/*, /events/*, /attendance/*, etc.",
        "public_endpoints": list(PUBLIC_ENDPOINTS),
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def gateway_proxy(request: Request, path: str) -> Response:
    """Основной proxy endpoint для пересылки запросов в микросервисы"""
    
    full_path = f"/{path}"
    
    # Проверка аутентификации для приватных эндпоинтов
    if not is_public_endpoint(full_path):
        auth_valid = await validate_auth_headers(request)
        if not auth_valid:
            logger.warning(f"🚫 Unauthorized access attempt to {full_path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized. Valid token required."}
            )
    
    # Получение URL микросервиса
    service_url = get_service_url(full_path)
    
    if not service_url:
        logger.warning(f"⚠️  No service found for path: {full_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service found for path: {full_path}. Available routes: {list(SERVICE_ROUTES.keys())}",
        )
    
    return await forward_request(request, service_url, full_path)


@app.on_event("startup")
async def startup_event() -> None:
    """Инициализация при запуске Gateway"""
    logger.info(f"🚀 CHUPAPUPA API Gateway v2.0 starting in {settings.ENVIRONMENT} mode")
    logger.info(f"🌐 Listening on {settings.HOST}:{settings.PORT}")
    logger.info(f"🔗 Available services: {len(SERVICE_ROUTES)}")
    
    for route, url in SERVICE_ROUTES.items():
        logger.info(f"   {route} -> {url}")
    
    logger.info(f"🔒 Public endpoints: {len(PUBLIC_ENDPOINTS)}")
    logger.info(f"🌍 CORS origins: {settings.CORS_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Очистка при остановке Gateway"""
    await http_client.aclose()
    logger.info("🚫 CHUPAPUPA API Gateway v2.0 stopped")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gateway:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
