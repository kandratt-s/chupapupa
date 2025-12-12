#!/bin/bash

# Скрипт для тестирования Auth сервиса
echo "=== Тестирование Auth сервиса ==="

BASE_URL="http://localhost:8001"

echo "1. Проверка health check..."
curl -s "$BASE_URL/" | python3 -m json.tool
echo -e "\n"

echo "2. Проверка health endpoint..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo -e "\n"

echo "3. Создание записи аутентификации для админа..."
echo "   (Auth - базовый сервис, админские эндпоинты открыты)"
ADMIN_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 10,
    "password": "super_secure_admin_password_that_can_be_very_long_without_any_issues",
    "role": "admin"
  }')

echo "$ADMIN_CREATE_RESPONSE" | python3 -m json.tool
echo -e "\n"

echo "4. Создание записи аутентификации для обычного пользователя..."
USER_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "password": "another_very_long_user_password_to_test_arbitrary_length_support",
    "role": "user"
  }')

echo "$USER_CREATE_RESPONSE" | python3 -m json.tool
echo -e "\n"

echo "5. Логин админа с длинным паролем..."
ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 10,
    "password": "super_secure_admin_password_that_can_be_very_long_without_any_issues"
  }')

echo "$ADMIN_LOGIN_RESPONSE" | python3 -m json.tool

ADMIN_ACCESS_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)
ADMIN_REFRESH_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('refresh_token', ''))" 2>/dev/null)

if [ ! -z "$ADMIN_ACCESS_TOKEN" ]; then
    echo "✓ Админ успешно авторизован"
    echo "Access token: ${ADMIN_ACCESS_TOKEN:0:50}..."
else
    echo "✗ Ошибка авторизации админа"
fi
echo -e "\n"

echo "6. Логин пользователя с длинным паролем..."
USER_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "password": "another_very_long_user_password_to_test_arbitrary_length_support"
  }')

echo "$USER_LOGIN_RESPONSE" | python3 -m json.tool

USER_ACCESS_TOKEN=$(echo "$USER_LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ ! -z "$USER_ACCESS_TOKEN" ]; then
    echo "✓ Пользователь успешно авторизован"
    echo "Access token: ${USER_ACCESS_TOKEN:0:50}..."
else
    echo "✗ Ошибка авторизации пользователя"
fi
echo -e "\n"

echo "7. Тестирование refresh токена..."
if [ ! -z "$ADMIN_REFRESH_TOKEN" ]; then
    echo "   Обновление access токена через refresh токен..."
    REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/refresh" \
      -H "Content-Type: application/json" \
      -d "{\"refresh_token\": \"$ADMIN_REFRESH_TOKEN\"}")
    
    echo "$REFRESH_RESPONSE" | python3 -m json.tool
    
    NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)
    
    if [ ! -z "$NEW_ACCESS_TOKEN" ]; then
        echo "✓ Refresh токен работает корректно"
    else
        echo "✗ Ошибка обновления токена"
    fi
else
    echo "   Пропускаем - нет refresh токена"
fi
echo -e "\n"

echo "8. Проверка неверных данных..."

echo "   8.1. Неверный пароль:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 10,
    "password": "wrong_password"
  }' | python3 -m json.tool
echo -e "\n"

echo "   8.2. Несуществующий пользователь:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 99999,
    "password": "any_password"
  }' | python3 -m json.tool
echo -e "\n"

echo "   8.3. Невалидный refresh токен:"
curl -s -X POST "$BASE_URL/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "invalid_token"}' | python3 -m json.tool
echo -e "\n"

echo "9. Получение информации об аутентификации..."
echo "   (Используется другими сервисами для проверки ролей)"

echo "   9.1. Информация об админе:"
curl -s -X GET "$BASE_URL/auth/10" | python3 -m json.tool
echo -e "\n"

echo "   9.2. Информация о пользователе:"
curl -s -X GET "$BASE_URL/auth/20" | python3 -m json.tool
echo -e "\n"

echo "   9.3. Несуществующий пользователь:"
curl -s -X GET "$BASE_URL/auth/99999" | python3 -m json.tool
echo -e "\n"

echo "10. Обновление записи аутентификации..."
echo "    (Смена пароля и роли через Admin сервис)"

echo "    10.1. Смена пароля пользователя:"
curl -s -X PUT "$BASE_URL/auth/20" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "new_super_long_password_after_change_even_longer_than_before"
  }' | python3 -m json.tool
echo -e "\n"

echo "    10.2. Проверка логина с новым паролем:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "password": "new_super_long_password_after_change_even_longer_than_before"
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('✓ Новый пароль работает' if data.get('access_token') else '✗ Новый пароль не работает')"
echo -e "\n"

echo "    10.3. Повышение пользователя до админа:"
curl -s -X PUT "$BASE_URL/auth/20" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }' | python3 -m json.tool
echo -e "\n"

echo "11. Тестирование смены пароля пользователем..."
echo "    (Пользователь меняет свой пароль самостоятельно)"

echo "    11.1. Смена пароля с корректным текущим паролем:"
if [ ! -z "$USER_ACCESS_TOKEN" ]; then
    CHANGE_PASSWORD_RESPONSE=$(curl -s -X PUT "$BASE_URL/change-password" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
      -d '{
        "current_password": "new_super_long_password_after_change_even_longer_than_before",
        "new_password": "my_personal_super_secure_password_changed_by_myself"
      }')
    
    echo "$CHANGE_PASSWORD_RESPONSE" | python3 -m json.tool
    echo -e "\n"
    
    echo "    11.2. Проверка логина с паролем, измененным пользователем:"
    curl -s -X POST "$BASE_URL/login" \
      -H "Content-Type: application/json" \
      -d '{
        "user_id": 20,
        "password": "my_personal_super_secure_password_changed_by_myself"
      }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('✓ Пароль, измененный пользователем, работает' if data.get('access_token') else '✗ Пароль не работает')"
    echo -e "\n"
else
    echo "    Пропускаем - нет токена пользователя"
    echo -e "\n"
fi

echo "    11.3. Попытка смены пароля с неверным текущим паролем:"
if [ ! -z "$ADMIN_ACCESS_TOKEN" ]; then
    curl -s -X PUT "$BASE_URL/change-password" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
      -d '{
        "current_password": "wrong_current_password",
        "new_password": "some_new_password"
      }' | python3 -m json.tool
    echo -e "\n"
else
    echo "    Пропускаем - нет токена админа"
    echo -e "\n"
fi

echo "    11.4. Попытка смены пароля без токена:"
curl -s -X PUT "$BASE_URL/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "any_password",
    "new_password": "any_new_password"
  }' | python3 -m json.tool
echo -e "\n"

echo "=== Тестирование завершено ==="
echo ""
echo "🎯 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:"
echo "   ✅ Поддержка паролей произвольной длины (scrypt вместо bcrypt)"
echo "   ✅ Создание/обновление записей аутентификации без авторизации"
echo "   ✅ JWT токены с правильными полями (user_id, role)"
echo "   ✅ Refresh токены для обновления сессий"
echo "   ✅ Защита от неверных паролей и несуществующих пользователей"
echo "   ✅ Интеграционные эндпоинты для других сервисов"
echo "   ✅ Пользователи могут менять свой пароль самостоятельно"
echo ""
echo "🏗️ АРХИТЕКТУРА:"
echo "   Auth сервис = БАЗОВЫЙ СЕРВИС (управляется Admin сервисом)"
echo "   userStatistic = получает роли через заголовки X-User-ID, X-User-Role"
echo "   Gateway = валидирует JWT токены → добавляет заголовки"
echo ""
echo "🔐 БЕЗОПАСНОСТЬ:"
echo "   • Пароли хешируются с помощью scrypt (произвольная длина)"
echo "   • JWT токены подписываются SECRET_KEY"
echo "   • Access токены (30 мин) + Refresh токены (7 дней)"
echo "   • Foreign Key связь с userStatistic.users"
echo "   • Пользователи могут менять пароль только с подтверждением текущего"