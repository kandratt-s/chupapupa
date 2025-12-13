# =================================================================
# Dockerfile для Event микросервиса
#
# Основан на официальном Python образе
# Оптимизирован для production развертывания
# =================================================================

FROM python:3.11-slim

# Метаданные
LABEL maintainer="ВШЭ Team"
LABEL description="Event Management Microservice"
LABEL version="1.0.0"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создаем пользователя для безопасности
RUN groupadd -r eventuser && useradd -r -g eventuser eventuser

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Устанавливаем права на файлы
RUN chown -R eventuser:eventuser /app

# Переключаемся на обычного пользователя
USER eventuser

# Порт, который будет использовать приложение
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
