FROM python:3.12-slim

# Устанавливаем системные зависимости для healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности с фиксированным UID=1000
# для совместимости с общими томами
RUN groupadd -r -g 1000 authuser && useradd -r -g authuser -u 1000 authuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Меняем владельца файлов
RUN chown -R authuser:authuser /app

# Переключаемся на непривилегированного пользователя
USER authuser

# Открываем порт
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
