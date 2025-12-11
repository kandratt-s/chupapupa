# =================================================================
# Dockerfile для userStatistic микросервиса
# Микросервис для управления пользователями и статистикой
# =================================================================

# Используем официальный Python slim образ
# slim версия меньше по размеру и безопаснее
FROM python:3.12-slim

# Метаданные образа
LABEL maintainer="chupapupa-team"
LABEL service="userstatistic"
LABEL version="1.0.0"
LABEL description="Микросервис для управления пользователями и статистикой"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создание непривилегированного пользователя
RUN useradd --create-home --shell /bin/bash --user-group app

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Обновление pip и установка зависимостей
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Передача прав на файлы пользователю app
RUN chown -R app:app /app

# Переключение на непривилегированного пользователя
USER app

# Настройка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Порт, который будет доступен снаружи (только для документации)
# В продакшене порт задается через переменную окружения
EXPOSE 8006

# Health check для мониторинга
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Команда запуска приложения
# Используем uvicorn напрямую
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8006", \
     "--workers", "4", \
     "--log-level", "info"]
