# UserStatistic Микросервис

Микросервис для управления пользователями и статистикой в системе chupapupa.

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/kandratt-s/chupapupa.git
cd chupapupa/services/userStatistic
```

### 2. Конфигурация окружения
```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env файл со своими настройками
nano .env
```

### 3. Запуск для локальной разработки
```bash
# С Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Либо локально с Python
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8006 --reload
```

## 🔧 Конфигурация

### Основные параметры в .env:

| Параметр | Описание | По умолчанию |
|------------|-------------|----------------|
| `SERVICE_NAME` | Название сервиса | `userstatistic-service` |
| `HOST` | Хост для привязки | `0.0.0.0` |
| `PORT` | Порт сервиса | `8006` |
| `DATABASE_URL` | Строка подключения к БД | - |
| `DB_HOST` | Хост БД | `postgres` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_PASSWORD` | Пароль БД | - |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## 📜 API Документация

После запуска сервиса документация API доступна по адресам:
- **Swagger UI**: http://localhost:8006/docs
- **ReDoc**: http://localhost:8006/redoc
- **Health Check**: http://localhost:8006/health

### Основные эндпоинты:

#### Для обычных пользователей:
- `GET /users/me` - Получить свой профиль
- `GET /users/{id}` - Получить профиль пользователя

#### Для Telegram бота:
- `POST /telegram/auth` - Авторизация через Telegram
- `GET /telegram/profile` - Получить свой профиль
- `GET /telegram/users` - [👑 ADMIN] Список пользователей

#### Для администраторов:
- `GET /admin/users` - Список всех пользователей
- `POST /admin/users` - Создать пользователя
- `PUT /admin/users/{id}` - Обновить пользователя
- `PATCH /admin/users/{id}/points` - Изменить баллы

## 🚀 Деплой в продакшен

### Вариант 1: Docker Compose (рекомендуемый)

1. **Подготовка сервера:**
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Клонирование и конфигурация:**
```bash
git clone https://github.com/kandratt-s/chupapupa.git
cd chupapupa/services/userStatistic

# Копирование конфига
cp .env.example .env

# Редактирование продакшен конфига
nano .env
```

3. **Обязательные изменения в .env:**
```bash
# Должен быть надежный пароль!
DB_PASSWORD=your_super_secure_password_here_2024

# Продакшен база данных
DATABASE_URL=postgresql://postgres:your_super_secure_password_here_2024@postgres:5432/chupapupa_db

# Логирование для продакшена
LOG_LEVEL=WARNING
```

4. **Запуск:**
```bash
# Сборка и запуск
docker-compose up -d --build

# Проверка статуса
docker-compose ps
curl http://localhost:8006/health
```

### Вариант 2: Отдельный Docker контейнер

```bash
# Сборка образа
docker build -t userstatistic:latest .

# Запуск с переменными окружения
docker run -d \
  --name userstatistic-service \
  --env-file .env \
  -p 8006:8006 \
  userstatistic:latest
```

### Вариант 3: Kubernetes

Создайте ConfigMap и Secret для конфигурации:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: userstatistic-config
data:
  SERVICE_NAME: "userstatistic-service"
  HOST: "0.0.0.0"
  PORT: "8006"
  LOG_LEVEL: "WARNING"
---
apiVersion: v1
kind: Secret
metadata:
  name: userstatistic-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@postgres:5432/db"
  DB_PASSWORD: "your_secure_password"
```

## 📊 Мониторинг

### Health Check эндпоинты:
- `GET /health` - Основная проверка здоровья
- `GET /` - Информация о сервисе

### Логи:
```bash
# Просмотр логов Docker
docker-compose logs -f userstatistic

# Последние 100 строк
docker-compose logs --tail=100 userstatistic
```

## 🔒 Безопасность

### Рекомендации по безопасности:

1. **Пароли базы данных:**
   - Используйте сложные пароли (16+ символов)
   - Никогда не коммитьте .env файлы

2. **Сеть:**
   - Ограничьте доступ к порту 8006 только для API Gateway
   - Используйте HTTPS в продакшене

3. **Обновления:**
   - Регулярно обновляйте зависимости
   - Мониторьте уязвимости

## 👥 Командная работа

### Для коллег по команде:

1. **Клонирование проекта:**
```bash
git clone https://github.com/kandratt-s/chupapupa.git
cd chupapupa/services/userStatistic
```

2. **Настройка окружения:**
```bash
cp .env.example .env
# Отредактируйте .env с локальными настройками
```

3. **Совместные настройки (передача коллегам):**

**ОПЦИЯ 1: Отдельный конфиг файл**
```bash
# Создайте team-config.env для общих настроек
echo "DB_HOST=shared-postgres.company.com" > team-config.env
echo "DB_PORT=5432" >> team-config.env
echo "DB_NAME=chupapupa_dev" >> team-config.env
# Перешлите коллегам
```

**ОПЦИЯ 2: Docker Compose override**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  userstatistic:
    environment:
      - DATABASE_URL=postgresql://user:pass@shared-db:5432/chupapupa_dev
      - LOG_LEVEL=DEBUG
```

**ОПЦИЯ 3: Корпоративный secrets manager**
```bash
# Пример с AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id "chupapupa/userstatistic/dev" --query SecretString --output text > .env
```

## 🔄 CI/CD

### GitHub Actions пример:
```yaml
# .github/workflows/deploy-userstatistic.yml
name: Deploy UserStatistic Service

on:
  push:
    branches: [ main ]
    paths: [ 'services/userStatistic/**' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Build and Deploy
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
      run: |
        cd services/userStatistic
        docker build -t userstatistic:${{ github.sha }} .
        # Дальнейший деплой...
```

---

## 📞 Поддержка

- **Технические вопросы**: откройте issue в GitHub
- **Документация API**: `/docs` после запуска сервиса
- **Логи**: `docker-compose logs userstatistic`
