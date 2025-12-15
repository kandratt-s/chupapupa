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
import jwt
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.base import BaseHTTPMiddleware
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

    # URL микросервисов (внутренние адреса) - правильные порты
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
    EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8004")
    ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://attendance-service:8003")
    USER_STATISTIC_SERVICE_URL = os.getenv("USER_STATISTIC_SERVICE_URL", "http://user-statistic-service:8006")
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

print("🔥 FastAPI app created!")
logger.info("🔥 FastAPI app created!")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🔥 CORS middleware added!")
logger.info("🔥 CORS middleware added!")

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


def is_public_endpoint(path: str) -> bool:
    """Проверяет, является ли эндпоинт публичным"""
    return any(path.startswith(endpoint) or path == endpoint.rstrip("/") 
              for endpoint in PUBLIC_ENDPOINTS)


def decode_jwt_token(token: str) -> Optional[Dict]:
    """Декодирует JWT токен и возвращает payload"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("🟡 JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"🟡 Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ JWT decode error: {e}")
        return None


async def validate_web_auth(request: Request) -> Optional[Dict]:
    """Валидация веб авторизации через JWT токен"""
    auth_header = request.headers.get("Authorization")
    logger.info(f"🔍 validate_web_auth: auth_header = {auth_header}")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.info("❌ No Bearer token found")
        return None
    
    token = auth_header.split(" ")[1]
    logger.info(f"🔍 Token extracted: {token[:50]}...")
    
    result = decode_jwt_token(token)
    logger.info(f"🔍 JWT decode result: {result}")
    
    return result


async def validate_telegram_auth(request: Request) -> Optional[Dict]:
    """Валидация Telegram авторизации через специальные заголовки"""
    # Проверяем наличие Telegram ID в заголовках
    tg_id = request.headers.get("X-Telegram-ID")
    tg_username = request.headers.get("X-Telegram-Username")
    
    if not tg_id:
        return None
        
    # TODO: Здесь можно добавить дополнительную валидацию Telegram auth
    # Например, проверку подписи или запрос к Bot API
    
    try:
        # Простая валидация формата Telegram ID
        telegram_id = int(tg_id)
        return {
            "telegram_id": telegram_id,
            "username": tg_username,
            "role": "user",  # По умолчанию все Telegram пользователи имеют роль "user"
            "auth_type": "telegram"
        }
    except ValueError:
        logger.warning(f"🟡 Invalid Telegram ID format: {tg_id}")
        return None


async def process_request_with_jwt(request: Request, path: str) -> Response:
    """Обрабатывает запрос и проксирует его в соответствующий микросервис"""
    service_url = get_service_url(path)
    
    if not service_url:
        logger.warning(f"🔴 No service found for path: {path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Service not found", "message": f"No service configured for path: {path}"}
        )
    
    # Формируем URL для проксирования
    target_path = path
    for route_prefix in SERVICE_ROUTES.keys():
        if path.startswith(route_prefix):
            target_path = path[len(route_prefix):]
            break
    
    target_url = f"{service_url}{target_path}"
    
    logger.info(f"🔄 Proxying {request.method} {path} -> {target_url}")
    
    try:
        # Подготавливаем заголовки (исключаем host)
        headers = dict(request.headers)
        headers.pop("host", None)
        
        # Выполняем запрос к микросервису
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
            timeout=httpx.Timeout(30.0)
        )
        
        logger.info(f"✅ Proxied to {target_url} - {response.status_code}")
        
        # Возвращаем ответ от микросервиса
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
        
    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout when proxying to {target_url}")
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"error": "Gateway Timeout", "message": f"Service {service_url} is not responding"}
        )
    except httpx.RequestError as e:
        logger.error(f"🔴 Request error when proxying to {target_url}: {e}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "Bad Gateway", "message": f"Could not connect to {service_url}"}
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error when proxying to {target_url}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal Gateway Error", "message": str(e)}
        )


def get_service_url(path: str) -> Optional[str]:
    """Определяет URL микросервиса по пути запроса"""
    # Сортируем маршруты по длине (сначала самые длинные) для точного совпадения
    sorted_routes = sorted(SERVICE_ROUTES.items(), key=lambda x: len(x[0]), reverse=True)
    
    for route_prefix, service_url in sorted_routes:
        if path.startswith(route_prefix):
            return service_url
    return None


@app.middleware("http")
async def auth_middleware(request: Request, call_next) -> Response:
    """Middleware для авторизации запросов"""
    path = str(request.url.path)
    
    print(f"🆘 AUTH MIDDLEWARE STARTED: {path}")
    logger.info(f"🆘 AUTH MIDDLEWARE STARTED: {path}")
    logger.info(f"🔍 Auth middleware processing: {path}")
    
    # Определяем роуты Gateway (не требуют проксирования)
    gateway_routes = {"/health", "/stats", "/", "/auth-info", "/routes", "/docs", "/redoc", "/openapi.json"}
    
    # Если это роут Gateway, передаём управление дальше
    if path in gateway_routes:
        logger.info(f"⚡ Gateway route, passing through: {path}")
        response = await call_next(request)
        return response
    
    logger.info(f"🔄 Proxy route, processing: {path}")
    
    # Пропускаем публичные эндпоинты
    if is_public_endpoint(path):
        logger.info(f"⚪ Public endpoint, skipping auth: {path}")
        return await process_request_with_jwt(request, path)
    
    logger.info(f"🔒 Private endpoint, checking auth: {path}")
    
    # Пытаемся авторизовать через веб (JWT)
    web_auth = await validate_web_auth(request)
    telegram_auth = await validate_telegram_auth(request)
    
    auth_data = web_auth or telegram_auth
    
    logger.info(f"🔍 Auth data: {auth_data}")
    
    if not auth_data:
        logger.warning(f"🔒 Unauthorized access attempt to {path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Authentication required", "message": "No valid authentication provided"}
        )
    
    # Добавляем информацию об авторизации в заголовки для микросервисов
    if auth_data.get("auth_type") == "telegram":
        # Telegram авторизация
        request.headers.__dict__["_list"].append((
            b"x-user-telegram-id", str(auth_data["telegram_id"]).encode()
        ))
        if auth_data.get("user_id"):
            request.headers.__dict__["_list"].append((
                b"x-user-id", str(auth_data["user_id"]).encode()
            ))
        if auth_data.get("username"):
            request.headers.__dict__["_list"].append((
                b"x-user-username", auth_data["username"].encode()
            ))
    else:
        # Веб авторизация (JWT)
        request.headers.__dict__["_list"].append((
            b"x-user-id", str(auth_data["user_id"]).encode()
        ))
    
    # Роль пользователя (общая для обоих типов авторизации)
    request.headers.__dict__["_list"].append((
        b"x-user-role", auth_data.get("role", "user").encode()
    ))
    
    # Тип авторизации
    request.headers.__dict__["_list"].append((
        b"x-auth-type", auth_data.get("auth_type", "web").encode()
    ))
    
    logger.info(f"✅ Authorized {auth_data.get('auth_type', 'web')} user {auth_data.get('user_id', auth_data.get('telegram_id'))} for {path}")
    
    # Проксируем запрос с добавленными заголовками
    return await process_request_with_jwt(request, path)


print("🔥 auth_middleware function defined!")
logger.info("🔥 auth_middleware function defined!")


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


async def validate_auth_headers(request: Request) -> bool:
    """Проверяет валидность авторизации пользователя"""
    # Пытаемся авторизовать через веб (JWT)
    web_auth = await validate_web_auth(request)
    telegram_auth = await validate_telegram_auth(request)
    
    return bool(web_auth or telegram_auth)


async def forward_request_with_headers(
    request: Request,
    service_url: str,
    path: str,
    custom_headers: Dict[str, str],
) -> Response:
    """Пересылает запрос в соответствующий микросервис с кастомными заголовками"""
    try:
        # Подготовка URL для микросервиса - убираем префикс Gateway
        service_path = path
        matched_prefix = None
        
        # Находим наиболее точное совпадение префикса
        for route_prefix in sorted(SERVICE_ROUTES.keys(), key=len, reverse=True):
            if path.startswith(route_prefix):
                matched_prefix = route_prefix
                service_path = path[len(route_prefix):]
                break

        # Если путь пустой после обрезания префикса, делаем его корневым
        if not service_path or service_path == "/":
            service_path = ""
        
        # Убеждаемся, что путь начинается с / если он не пустой
        elif service_path and not service_path.startswith("/"):
            service_path = "/" + service_path

        target_url = f"{service_url}{service_path}"

        # Копирование заголовков (исключая hop-by-hop заголовки)
        headers = custom_headers
        excluded_headers = ["host", "connection", "upgrade", "proxy-connection"]
        for header in excluded_headers:
            headers.pop(header, None)

        # Получение тела запроса
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

        logger.debug(f"📤 Forwarding {request.method} {path} -> {target_url} (prefix: {matched_prefix}) with custom headers")

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


async def forward_request(
    request: Request,
    service_url: str,
    path: str,
) -> Response:
    """Пересылает запрос в соответствующий микросервис"""
    try:
        # Подготовка URL для микросервиса - убираем префикс Gateway
        service_path = path
        matched_prefix = None
        
        # Находим наиболее точное совпадение префикса
        for route_prefix in sorted(SERVICE_ROUTES.keys(), key=len, reverse=True):
            if path.startswith(route_prefix):
                matched_prefix = route_prefix
                service_path = path[len(route_prefix):]
                break

        # Если путь пустой после обрезания префикса, делаем его корневым
        if not service_path or service_path == "/":
            service_path = ""
        
        # Убеждаемся, что путь начинается с / если он не пустой
        elif service_path and not service_path.startswith("/"):
            service_path = "/" + service_path

        target_url = f"{service_url}{service_path}"

        # Копирование заголовков (исключая hop-by-hop заголовки)
        headers = dict(request.headers)
        excluded_headers = ["host", "connection", "upgrade", "proxy-connection"]
        for header in excluded_headers:
            headers.pop(header, None)

        # Получение тела запроса
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

        logger.debug(f"📤 Forwarding {request.method} {path} -> {target_url} (prefix: {matched_prefix})")

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


@app.get("/auth-info")
async def auth_info() -> dict:
    """Информация о системе авторизации Gateway"""
    return {
        "service": "CHUPAPUPA API Gateway v2.0 - Authentication System",
        "status": "running", 
        "authentication_types": {
            "web": {
                "description": "JWT токены для веб-приложений",
                "flow": "POST /auth/login -> получить JWT -> Authorization: Bearer {token}",
                "headers_added": ["x-user-id", "x-user-role", "x-auth-type=web"]
            },
            "telegram": {
                "description": "Авторизация через Telegram бота",
                "flow": "Заголовки X-Telegram-ID + X-Telegram-Username -> автоматическая проверка",
                "headers_added": ["x-user-telegram-id", "x-user-id", "x-user-role", "x-auth-type=telegram", "x-user-username"]
            }
        },
        "proxy_headers": {
            "description": "Заголовки, добавляемые Gateway для микросервисов",
            "common": [
                "x-user-role: роль пользователя (user/admin)",
                "x-auth-type: тип авторизации (web/telegram)"
            ],
            "web_specific": [
                "x-user-id: ID пользователя из JWT токена"
            ],
            "telegram_specific": [
                "x-user-telegram-id: Telegram ID пользователя",
                "x-user-id: ID пользователя (при наличии)",
                "x-user-username: Telegram username (при наличии)"
            ]
        },
        "public_endpoints": list(PUBLIC_ENDPOINTS),
        "timestamp": time.time()
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


# Примечание: uvicorn.run не нужен, так как приложение запускается через Docker
# с командой: uvicorn gateway:app --host 0.0.0.0 --port 8000