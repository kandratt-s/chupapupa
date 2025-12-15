#!/bin/bash

# Скрипт создания структуры папок для хранения фотографий
# Используется в Docker контейнере photos-volume

echo "🔧 Создание структуры папок для фотографий..."

# Основная директория для всех фотографий
PHOTOS_BASE="/shared/photos"

# Создаем основные папки
mkdir -p "$PHOTOS_BASE/faces"
mkdir -p "$PHOTOS_BASE/attendances"

# Создаем подпапки для userStatistic service (лица пользователей)
# Структура: /shared/photos/faces/user_id.формат
mkdir -p "$PHOTOS_BASE/faces/raw" 
mkdir -p "$PHOTOS_BASE/faces/processed"
mkdir -p "$PHOTOS_BASE/faces/thumbnails"

# Создаем подпапки для attendance service (файлы посещений)
# Структура: /shared/photos/attendances/attendance_id.формат
mkdir -p "$PHOTOS_BASE/attendances/uploads"
mkdir -p "$PHOTOS_BASE/attendances/verified"
mkdir -p "$PHOTOS_BASE/attendances/thumbnails"

# Создаем временную папку для обработки
mkdir -p "$PHOTOS_BASE/temp"

# Установка правильных прав доступа
chmod -R 755 "$PHOTOS_BASE"

# Создание файла README с описанием структуры
cat > "$PHOTOS_BASE/README.md" << 'EOF'
# Структура папок для фотографий CHUPAPUPA

## /shared/photos/faces/
Фотографии пользователей для userStatistic service:

### Основная папка: `/shared/photos/faces/`
- Файлы сохраняются как: `user_id.формат` (например: `123.jpg`, `456.png`)
- При регистрации нового пользователя фото сохраняется с именем user_id

### Подпапки:
- `/raw/` - исходные загруженные фотографии пользователей
- `/processed/` - обработанные фотографии после анализа лиц
- `/thumbnails/` - миниатюры для быстрого отображения (200x200px)

## /shared/photos/attendances/
Файлы посещений для attendance service:

### Основная папка: `/shared/photos/attendances/`
- Файлы сохраняются как: `attendance_id.формат` (например: `789.pdf`, `101.jpg`)
- При отправке attendance заявки файл сохраняется с именем attendance_id

### Подпапки:
- `/uploads/` - загруженные файлы (PNG, JPEG, PDF, GIF, DOC, DOCX и др.)
- `/verified/` - проверенные администратором файлы
- `/thumbnails/` - миниатюры для предварительного просмотра

## /shared/photos/temp/
Временные файлы для обработки:
- Промежуточные файлы при загрузке
- Файлы в процессе конвертации
- Автоматическая очистка каждые 24 часа

## Права доступа
Все папки: 755 (rwxr-xr-x)
Файлы: 644 (rw-r--r--)

## Использование в сервисах

### userStatistic service:
- Основная папка: `/shared/photos/faces/`
- Сохранение при регистрации: `/shared/photos/faces/user_{user_id}.{ext}`
- Обработка: копирование в `/processed/` после анализа лица
- Миниатюры: автогенерация в `/thumbnails/`

### attendance service:
- Основная папка: `/shared/photos/attendances/`
- Сохранение заявки: `/shared/photos/attendances/attendance_{attendance_id}.{ext}`
- Проверка админом: перемещение в `/verified/` после одобрения
- Миниатюры: автогенерация для изображений в `/thumbnails/`

## Примеры путей файлов

### Пользователь ID 123 загружает фото при регистрации:
- Исходный файл: `/shared/photos/faces/user_123.jpg`
- Обработанный: `/shared/photos/faces/processed/user_123_processed.jpg`
- Миниатюра: `/shared/photos/faces/thumbnails/user_123_thumb.jpg`

### Заявка на посещение ID 789:
- Загруженный файл: `/shared/photos/attendances/attendance_789.pdf`
- Проверенный файл: `/shared/photos/attendances/verified/attendance_789_verified.pdf`
- Миниатюра (если изображение): `/shared/photos/attendances/thumbnails/attendance_789_thumb.jpg`
EOF

echo "✅ Структура папок создана успешно:"
echo "📁 $PHOTOS_BASE/faces/"
echo "   ├── raw/"
echo "   ├── processed/"  
echo "   └── thumbnails/"
echo "📁 $PHOTOS_BASE/attendances/"
echo "   ├── uploads/"
echo "   ├── verified/"
echo "   └── thumbnails/"
echo "📁 $PHOTOS_BASE/temp/"
echo ""
echo "📄 README.md с подробным описанием создан"
echo "🔒 Права доступа установлены: 755"
echo "👤 Формат файлов пользователей: user_id.формат"
echo "📝 Формат файлов посещений: attendance_id.формат"