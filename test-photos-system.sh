#!/bin/bash

# Тестирование системы хранения фотографий CHUPAPUPA

echo "🧪 Тестирование системы хранения фотографий..."
echo

# Проверка структуры папок
echo "📁 Проверка структуры папок:"

if [ -d "photos/faces" ]; then
    echo "✅ photos/faces/ - существует"
else
    echo "❌ photos/faces/ - не найдена"
fi

if [ -d "photos/attendances" ]; then
    echo "✅ photos/attendances/ - существует"
else
    echo "❌ photos/attendances/ - не найдена"
fi

echo

# Тестирование создания тестовых файлов
echo "📝 Создание тестовых файлов:"

# Создаем тестовую фотографию пользователя
echo "Тестовое фото пользователя" > photos/faces/123.jpg
if [ -f "photos/faces/123.jpg" ]; then
    echo "✅ Тестовое фото пользователя (123.jpg) создано"
else
    echo "❌ Не удалось создать тестовое фото пользователя"
fi

# Создаем тестовый файл посещения
echo "Тестовый файл посещения" > photos/attendances/456.pdf
if [ -f "photos/attendances/456.pdf" ]; then
    echo "✅ Тестовый файл посещения (456.pdf) создан"
else
    echo "❌ Не удалось создать тестовый файл посещения"
fi

echo

# Проверка путей в сервисах
echo "🔍 Проверка путей в сервисах:"

echo "UserStatistic сервис:"
if grep -q "/shared/photos" services/userStatistic/app/services/photo_service.py; then
    echo "✅ Использует правильный путь /shared/photos"
else
    echo "❌ Неправильный путь в userStatistic"
fi

echo "Attendance сервис:"
if grep -q "/shared/photos" services/attendance/src/services/photo_service.py; then
    echo "✅ Использует правильный путь /shared/photos"
else
    echo "❌ Неправильный путь в attendance"
fi

echo

# Проверка Docker конфигурации
echo "🐳 Проверка Docker конфигурации:"

if grep -q "photos_data:/shared/photos" docker-compose.yml; then
    echo "✅ Docker volume настроен правильно"
else
    echo "❌ Проблемы с Docker volume"
fi

if grep -q "PHOTOS_PATH=/shared/photos" docker-compose.yml; then
    echo "✅ Переменные окружения настроены правильно"
else
    echo "❌ Проблемы с переменными окружения"
fi

echo

# Проверка зависимостей
echo "📦 Проверка зависимостей:"

echo "UserStatistic requirements:"
if grep -q "aiofiles" services/userStatistic/requirements.txt && grep -q "Pillow" services/userStatistic/requirements.txt; then
    echo "✅ Необходимые зависимости (aiofiles, Pillow) присутствуют"
else
    echo "❌ Отсутствуют необходимые зависимости"
fi

echo "Attendance requirements:"
if grep -q "aiofiles" services/attendance/requirements.txt && grep -q "Pillow" services/attendance/requirements.txt; then
    echo "✅ Необходимые зависимости (aiofiles, Pillow) присутствуют"
else
    echo "❌ Отсутствуют необходимые зависимости"
fi

echo

# Проверка API эндпоинтов
echo "🌐 Проверка API эндпоинтов:"

if grep -q "upload_my_photo" services/userStatistic/app/api/users.py; then
    echo "✅ UserStatistic: эндпоинт загрузки фото найден"
else
    echo "❌ UserStatistic: эндпоинт загрузки фото отсутствует"
fi

if grep -q "save_attendance_photo" services/attendance/src/services/photo_service.py; then
    echo "✅ Attendance: метод сохранения фото найден"
else
    echo "❌ Attendance: метод сохранения фото отсутствует"
fi

echo

# Очистка тестовых файлов
echo "🧹 Очистка тестовых файлов:"
rm -f photos/faces/123.jpg photos/attendances/456.pdf
echo "✅ Тестовые файлы удалены"

echo
echo "🎉 Тестирование завершено!"
echo
echo "📋 Итоговая структура:"
echo "📁 /shared/photos/"
echo "  ├── faces/           <- фото пользователей (user_id.формат)"
echo "  └── attendances/     <- файлы посещений (attendance_id.формат)"
echo
echo "🔗 Доступ к файлам:"
echo "UserStatistic:  http://localhost:8006/static/faces/"
echo "Attendance:     http://localhost:8003/static/attendances/"
echo "Gateway:        http://localhost:8000/users/{user_id}/photo"
echo "                http://localhost:8000/attendances/..."