#!/bin/bash

# Скрипт для тестирования Auth сервиса ВШЭ
echo "=== Тестирование Auth сервиса ВШЭ ==="

BASE_URL="http://localhost:8001"
ADMIN_ID=1
STUDENT_ID=2
ADMIN_PASSWORD="super_secure_admin_password_that_can_be_very_long_without_any_issues"
STUDENT_PASSWORD="another_very_long_user_password_to_test_arbitrary_length_support"

echo "1. Проверка health check..."
curl -s "$BASE_URL/"
echo -e "\n"

echo "2. Проверка health endpoint..."
curl -s "$BASE_URL/health"
echo -e "\n"

echo "3. Создание записи аутентификации для админа..."
ADMIN_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$ADMIN_ID',
    "password": "'"$ADMIN_PASSWORD"'",
    "role": "admin"
  }')

echo "$ADMIN_CREATE_RESPONSE"
echo -e "\n"

echo "4. Создание записи аутентификации для студента..."
STUDENT_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$STUDENT_ID',
    "password": "'"$STUDENT_PASSWORD"'",
    "role": "user"
  }')

echo "$STUDENT_CREATE_RESPONSE"
echo -e "\n"

echo "5. Логин админа..."
ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$ADMIN_ID',
    "password": "'"$ADMIN_PASSWORD"'"
  }')

echo "$ADMIN_LOGIN_RESPONSE"

# Извлекаем токены
ADMIN_ACCESS_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    print('')
")

ADMIN_REFRESH_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('refresh_token', ''))
except:
    print('')
")

if [ ! -z "$ADMIN_ACCESS_TOKEN" ]; then
    echo "✅ Админ успешно авторизован"
else
    echo "❌ Ошибка авторизации админа"
fi
echo -e "\n"

echo "6. Логин студента..."
STUDENT_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$STUDENT_ID',
    "password": "'"$STUDENT_PASSWORD"'"
  }')

echo "$STUDENT_LOGIN_RESPONSE"

STUDENT_ACCESS_TOKEN=$(echo "$STUDENT_LOGIN_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    print('')
")

if [ ! -z "$STUDENT_ACCESS_TOKEN" ]; then
    echo "✅ Студент успешно авторизован"
else
    echo "❌ Ошибка авторизации студента"
fi
echo -e "\n"

echo "7. Тестирование refresh токена..."
if [ ! -z "$ADMIN_REFRESH_TOKEN" ]; then
    echo "Обновление access токена через refresh токен..."
    REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/refresh" \
      -H "Content-Type: application/json" \
      -d "{\"refresh_token\": \"$ADMIN_REFRESH_TOKEN\"}")

    echo "$REFRESH_RESPONSE"

    NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    print('')
")

    if [ ! -z "$NEW_ACCESS_TOKEN" ]; then
        echo "✅ Refresh токен работает корректно"
    else
        echo "❌ Ошибка обновления токена"
    fi
else
    echo "Пропускаем - нет refresh токена"
fi
echo -e "\n"

echo "8. Проверка неверных данных..."

echo "8.1. Неверный пароль:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$ADMIN_ID',
    "password": "wrong_password"
  }'
echo -e "\n"

echo "8.2. Несуществующий пользователь:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 99999,
    "password": "any_password"
  }'
echo -e "\n"

echo "8.3. Невалидный refresh токен:"
curl -s -X POST "$BASE_URL/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "invalid_token"}'
echo -e "\n"

echo "9. Получение информации об аутентификации..."
echo "9.1. Информация об админе:"
curl -s -X GET "$BASE_URL/auth/$ADMIN_ID"
echo -e "\n"

echo "9.2. Информация о студенте:"
curl -s -X GET "$BASE_URL/auth/$STUDENT_ID"
echo -e "\n"

echo "9.3. Несуществующий пользователь:"
curl -s -X GET "$BASE_URL/auth/99999"
echo -e "\n"

echo "10. Обновление записи аутентификации..."
echo "10.1. Смена пароля студента:"
curl -s -X PUT "$BASE_URL/auth/$STUDENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "new_super_long_password_after_change_even_longer_than_before"
  }'
echo -e "\n"

echo "10.2. Проверка логина с новым паролем:"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": '$STUDENT_ID',
    "password": "new_super_long_password_after_change_even_longer_than_before"
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('access_token'):
        print('✅ Новый пароль работает')
    else:
        print('❌ Новый пароль не работает')
except:
    print('❌ Ошибка проверки')
"
echo -e "\n"

echo "10.3. Повышение студента до админа:"
curl -s -X PUT "$BASE_URL/auth/$STUDENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
echo -e "\n"

echo "11. Тестирование смены пароля пользователем..."
if [ ! -z "$STUDENT_ACCESS_TOKEN" ]; then
    echo "11.1. Смена пароля с корректным текущим паролем:"
    curl -s -X PUT "$BASE_URL/change-password" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $STUDENT_ACCESS_TOKEN" \
      -d '{
        "current_password": "new_super_long_password_after_change_even_longer_than_before",
        "new_password": "my_personal_super_secure_password_changed_by_myself"
      }'
    echo -e "\n"
else
    echo "Пропускаем - нет токена студента"
fi

echo "11.2. Попытка смены пароля без токена:"
curl -s -X PUT "$BASE_URL/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "any_password",
    "new_password": "any_new_password"
  }'
echo -e "\n"

echo "=== Тестирование завершено ==="