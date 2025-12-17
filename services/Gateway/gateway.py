"""
CHUPAPUPA API Gateway v2.1 - Router with lightweight auth bridge.
Валидирует JWT и добавляет x-user-* заголовки при проксировании.
"""

import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict, cast

import httpx
import jwt
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

    # URL микросервисов
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
    EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8004")
    ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://attendance-service:8003")
    USER_STATISTIC_SERVICE_URL = os.getenv(
        "USER_STATISTIC_SERVICE_URL", "http://user-statistic-service:8006"
    )
    ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin-service:8000")
    BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot-service:8000")
    WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(
        ","
    )
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chupapupa-shared-super-secret-key-2025")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


settings = Settings()

# Конфигурация логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api-gateway-simple")

# Создание приложения
app = FastAPI(
    title="CHUPAPUPA API Gateway v2.1",
    description="Простой маршрутизатор для микросервисов CHUPAPUPA",
    version="2.1.0",
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

# HTTP клиент для проксирования
http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True)

# Маппинг маршрутов на микросервисы
SERVICE_ROUTES = {
    "/auth": settings.AUTH_SERVICE_URL,
    "/api/auth": settings.AUTH_SERVICE_URL,
    "/events": settings.EVENT_SERVICE_URL,
    "/api/events": settings.EVENT_SERVICE_URL,
    "/attendances": settings.ATTENDANCE_SERVICE_URL,
    "/api/attendances": settings.ATTENDANCE_SERVICE_URL,
    "/user-statistics": settings.USER_STATISTIC_SERVICE_URL,
    "/api/user-statistics": settings.USER_STATISTIC_SERVICE_URL,
    "/admin": settings.ADMIN_SERVICE_URL,
    "/api/admin": settings.ADMIN_SERVICE_URL,
    "/bot": settings.BOT_SERVICE_URL,
    "/api/bot": settings.BOT_SERVICE_URL,
    "/web": settings.WEB_SERVICE_URL,
    "/api/web": settings.WEB_SERVICE_URL,
}


class RequestStats(TypedDict):
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_response_time: float


# Статистика запросов
request_stats: RequestStats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_response_time": 0.0,
}


def decode_jwt_token(token: str) -> dict[str, Any]:
    """
    Декодирует и валидирует JWT токен от Auth сервиса.
    Возвращает payload с user_id и role.
    """
    try:
        payload: dict[str, Any] = cast(
            dict[str, Any],
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]),
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена"
            )
        if not payload.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="В токене нет user_id"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Срок действия токена истек"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен"
        ) from None


def build_user_headers(request: Request) -> tuple[dict[str, str], bool]:
    """
    Преобразует JWT из Authorization в явные заголовки для внутренних сервисов.
    Возвращает набор заголовков и флаг, что пользователь аутентифицирован.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return {}, False

    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt_token(token)

    user_headers = {
        "x-user-id": str(payload.get("user_id")),
        "x-user-role": str(payload.get("role", "user")),
        "x-auth-type": "jwt",
    }
    return user_headers, True


def get_service_url(path: str) -> str | None:
    """Определяет URL микросервиса по пути запроса"""
    # Сортируем маршруты по длине (сначала самые длинные) для точного совпадения
    sorted_routes = sorted(SERVICE_ROUTES.items(), key=lambda x: len(x[0]), reverse=True)

    for route_prefix, service_url in sorted_routes:
        if path.startswith(route_prefix):
            return service_url
    return None


async def proxy_request(request: Request, path: str) -> Response:
    """Проксирует запрос в соответствующий микросервис"""
    service_url = get_service_url(path)

    if not service_url:
        logger.warning(f"🔴 No service found for path: {path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Service not found",
                "message": f"No service configured for path: {path}",
            },
        )

    # Формируем URL для проксирования
    target_path = path
    for route_prefix in SERVICE_ROUTES.keys():
        if path.startswith(route_prefix):
            target_path = path[len(route_prefix) :]
            break

    target_url = f"{service_url}{target_path}"
    logger.info(f"🔄 Proxying {request.method} {path} -> {target_url}")

    try:
        # Подготавливаем заголовки (исключаем host)
        headers = dict(request.headers)
        headers.pop("host", None)

        # Добавляем заголовки пользователя из JWT, если он есть
        try:
            user_headers, authenticated = build_user_headers(request)
            if authenticated:
                headers.update(user_headers)
        except HTTPException as auth_exc:
            return JSONResponse(
                status_code=auth_exc.status_code,
                content={"error": "Unauthorized", "message": auth_exc.detail},
            )

        # Выполняем запрос к микросервису
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
            timeout=httpx.Timeout(30.0),
        )

        logger.info(f"✅ Proxied to {target_url} - {response.status_code}")

        # Возвращаем ответ от микросервиса
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )

    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout when proxying to {target_url}")
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "error": "Gateway Timeout",
                "message": f"Service {service_url} is not responding",
            },
        )
    except httpx.RequestError as e:
        logger.error(f"🔴 Request error when proxying to {target_url}: {e}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "Bad Gateway", "message": f"Could not connect to {service_url}"},
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error when proxying to {target_url}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal Gateway Error", "message": str(e)},
        )


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware для логирования"""
    start_time = time.time()
    request_stats["total_requests"] += 1

    # Логирование входящего запроса
    logger.info(
        "🔵 %s %s - Client: %s",
        request.method,
        request.url,
        request.client.host if request.client else "unknown",
    )

    try:
        # Если это Gateway роут, обрабатываем обычным способом
        path = str(request.url.path)
        if path in {"/health", "/stats", "/", "/docs", "/redoc", "/openapi.json"}:
            response = await call_next(request)
        else:
            # Иначе проксируем запрос
            response = await proxy_request(request, path)

        process_time = time.time() - start_time
        request_stats["total_response_time"] += process_time

        if response.status_code < 400:
            request_stats["successful_requests"] += 1
        else:
            request_stats["failed_requests"] += 1

        # Логирование ответа
        status_color = "🟢" if response.status_code < 400 else "🔴"
        logger.info(
            "%s %s %s - %s - %.3fs",
            status_color,
            request.method,
            request.url,
            response.status_code,
            process_time,
        )

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


class HealthResponse(BaseModel):
    """Ответ health check"""

    service: str
    status: str
    version: str
    environment: str
    services: dict[str, str]


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Проверка состояния Gateway и всех микросервисов"""
    services_status: dict[str, str] = {}

    for route, service_url in SERVICE_ROUTES.items():
        try:
            response = await http_client.get(f"{service_url}/health", timeout=5.0)
            services_status[route] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services_status[route] = "unavailable"

    # Определяем общий статус
    if all(status == "healthy" for status in services_status.values()):
        overall_status = "healthy"
    elif any(status == "healthy" for status in services_status.values()):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        service="api-gateway",
        status=overall_status,
        version="2.1.0",
        environment=settings.ENVIRONMENT,
        services=services_status,
    )


class ServiceStats(BaseModel):
    """Статистика сервисов"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float


@app.get("/stats", response_model=ServiceStats)
async def get_stats() -> ServiceStats:
    """Получение статистики работы Gateway"""
    avg_time = (
        request_stats["total_response_time"] / request_stats["total_requests"]
        if request_stats["total_requests"] > 0
        else 0.0
    )

    return ServiceStats(
        total_requests=request_stats["total_requests"],
        successful_requests=request_stats["successful_requests"],
        failed_requests=request_stats["failed_requests"],
        average_response_time=round(avg_time, 3),
    )


@app.get("/")
async def root() -> dict[str, Any]:
    """Корневой эндпоинт"""
    return {
        "service": "CHUPAPUPA API Gateway v2.1",
        "status": "running",
        "description": "Простой маршрутизатор для микросервисов",
        "available_routes": list(SERVICE_ROUTES.keys()),
    }


@app.on_event("startup")
async def startup_event() -> None:
    """Инициализация при запуске Gateway"""
    logger.info("🚀 CHUPAPUPA API Gateway v2.1 starting")
    logger.info("🌐 Listening on 0.0.0.0:8000")
    logger.info(f"🔗 Available services: {len(SERVICE_ROUTES)}")
    for route, service in SERVICE_ROUTES.items():
        logger.info(f"   {route} -> {service}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Очистка при остановке Gateway"""
    await http_client.aclose()
    logger.info("🚫 CHUPAPUPA API Gateway v2.1 stopped")
