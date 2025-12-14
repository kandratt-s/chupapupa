"""
Middleware компоненты для API Gateway.
"""

import logging
import time

from app.services.stats import stats_service
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("api-gateway")


async def logging_middleware(request: Request, call_next) -> Response:
    """Middleware для логирования и подсчета статистики"""
    start_time = time.time()
    stats_service.increment_total_requests()

    # Логирование входящего запроса
    logger.info(
        f"🔵 {request.method} {request.url} - Client: {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Обновление статистики
        stats_service.add_response_time(process_time)
        if response.status_code < 400:
            stats_service.increment_successful_requests()
        else:
            stats_service.increment_failed_requests()

        # Логирование ответа
        status_color = "🟢" if response.status_code < 400 else "🔴"
        logger.info(
            f"{status_color} {request.method} {request.url} - {response.status_code} - {process_time:.3f}s"
        )

        response.headers["X-Process-Time"] = str(process_time)
        return response

    except Exception as e:
        process_time = time.time() - start_time
        stats_service.increment_failed_requests()

        logger.error(f"🔴 {request.method} {request.url} - ERROR: {str(e)} - {process_time:.3f}s")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Gateway Error", "message": str(e)},
        )