FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности с фиксированным UID=1000
# для совместимости с общими томами
RUN groupadd -r -g 1000 attendanceuser && useradd -r -g attendanceuser -u 1000 attendanceuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем локальные директории для фото и устанавливаем права
# Основные фото будут в shared volume: /shared/photos/attendances/
RUN mkdir -p photos/attendances photos/attendances/thumbnails photos/temp && \
    chown -R attendanceuser:attendanceuser /app

# Переключаемся на пользователя
USER attendanceuser

# Открываем порт
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
