FROM python:3.11-slim

# Устанавливаем минимальные системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --retries 5 --timeout 120 \
    --trusted-host pypi.python.org --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    -r requirements.txt

# Копируем исходный код
COPY . .

EXPOSE 8501

# Запуск Streamlit в headless режиме
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=true", "--server.enableXsrfProtection=false"]