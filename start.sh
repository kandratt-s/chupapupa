#!/bin/bash

# 🚀 CHUPAPUPA Quick Start Script
# Этот скрипт поднимает всю систему одной командой

set -e  # Остановить при ошибке

echo "🚀 Запуск системы CHUPAPUPA..."
echo "=================================="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и повторите попытку."
    exit 1
fi

# Создание .env файла если не существует
if [ ! -f .env ]; then
    echo "📝 Создание .env файла из примера..."
    cp .env.example .env
    echo "✅ .env файл создан. Отредактируйте его при необходимости."
fi

# Остановка предыдущих контейнеров
echo "🛑 Остановка предыдущих контейнеров..."
docker-compose down --remove-orphans

# Сборка и запуск
echo "🏗️  Сборка и запуск контейнеров..."
docker-compose up --build -d

# Ожидание запуска базы данных
echo "⏳ Ожидание готовности базы данных..."
sleep 10

# Проверка статуса сервисов
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверка health check API Gateway
echo "🔍 Проверка работоспособности API Gateway..."
sleep 5

MAX_ATTEMPTS=12
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo "✅ API Gateway готов к работе!"
        break
    else
        echo "⏳ Попытка $ATTEMPT/$MAX_ATTEMPTS - ожидание готовности API Gateway..."
        sleep 5
        ATTEMPT=$((ATTEMPT + 1))
    fi
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "❌ API Gateway не отвечает. Проверьте логи:"
    echo "   docker-compose logs api-gateway"
    exit 1
fi

echo ""
echo "🎉 Система CHUPAPUPA успешно запущена!"
echo "=================================="
echo ""
echo "📍 Доступные интерфейсы:"
echo "   🌐 API Gateway:     http://localhost:8000"
echo "   📚 Документация:    http://localhost:8000/docs"
echo "   🏥 Health Check:    http://localhost:8000/health"
echo "   📈 Статистика:      http://localhost:8000/stats"
echo "   🗺️  Маршруты:       http://localhost:8000/routes"
echo "   🌍 Веб интерфейс:   http://localhost:3000"
echo ""
echo "📁 Структура фотографий:"
echo "   👤 Фото пользователей:  /shared/photos/faces/"
echo "   📝 Файлы посещений:     /shared/photos/attendances/"
echo ""
echo "🔧 Полезные команды:"
echo "   📋 Статус:             docker-compose ps"
echo "   📜 Логи всех сервисов:  docker-compose logs -f"
echo "   📜 Логи Gateway:        docker-compose logs -f api-gateway"
echo "   🛑 Остановить:          docker-compose down"
echo "   🗑️  Полная очистка:     docker-compose down -v --rmi all"
echo ""
echo "🎯 Готово к использованию!"