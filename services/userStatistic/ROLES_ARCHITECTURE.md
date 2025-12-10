"""
ДОКУМЕНТАЦИЯ: Управление ролями в микросервисной архитектуре
===========================================================

## 🏗️ АРХИТЕКТУРА РОЛЕЙ

### Правильное распределение ответственности:

**Auth Service:**
- Таблица: user_id, password_hash, role, email
- Функции: JWT токены, аутентификация, определение ролей
- Единственный источник истины для ролей

**UserStatistic Service:**
- Таблица: user_id, last_name, first_name, group_name, tg_id, practice_points, etc.
- Функции: Персональные данные, баллы, группы
- НЕ содержит роли - получает через заголовки

### 🔄 ПОТОК АВТОРИЗАЦИИ

#### Веб-интерфейс:
1. Пользователь → логин/пароль → Auth Service
2. Auth Service → проверяет credentials → генерирует JWT
3. Веб → запрос с JWT → API Gateway
4. API Gateway → валидирует JWT → добавляет заголовки (X-User-ID, X-User-Role)
5. UserStatistic → получает роль из заголовков

#### Telegram Bot:
1. Bot → запрос с X-Telegram-ID → API Gateway
2. API Gateway → Auth Service (по tg_id находит user_id и role)
3. API Gateway → добавляет заголовки (X-User-ID, X-User-Role)
4. UserStatistic → получает роль из заголовков

## ⚠️ ВАЖНЫЕ ПРИНЦИПЫ

### ✅ ПРАВИЛЬНО:
- Роль определяется только в Auth Service
- UserStatistic полагается на заголовки X-User-Role
- Единственный источник истины для ролей
- Централизованная система безопасности

### ❌ НЕПРАВИЛЬНО:
- Определять роль по group_name или email в UserStatistic
- Дублировать логику ролей в разных сервисах
- Хранить роли в userStatistic таблице
- Самодельные проверки админских прав

## 🔧 КОД ИЗМЕНЕНИЯ

### В telegram.py - УБРАЛИ:
```python
# НЕПРАВИЛЬНО - убрано:
is_admin = False
if user.группа and ("admin" in user.группа.lower()):
    is_admin = True
elif user.HSEmail and "admin" in user.HSEmail:
    is_admin = True
```

### В dependencies.py - УБРАЛИ:
```python
# НЕПРАВИЛЬНО - убрано:
if user.group_name and ("admin" in user.group_name.lower()):
    is_admin = True
elif user.hs_email and user.hs_email.endswith("@admin.university.edu"):
    is_admin = True
```

### ПРАВИЛЬНО - ТЕПЕРЬ:
```python
# Роль приходит от Auth Service через заголовки
role = current_user_info.get("role", "student")  # Fallback для разработки
```

## 🚀 TODO для продакшена:

1. **Реализовать Auth Service** полностью
2. **API Gateway** должен обращаться к Auth Service для проверки tg_id
3. **Убрать все fallback'и** и полагаться только на заголовки
4. **Добавить валидацию заголовков** от доверенного источника (API Gateway)

## 🛡️ БЕЗОПАСНОСТЬ

- UserStatistic НЕ должен самостоятельно определять роли
- Все проверки ролей через заголовки от Auth Service
- API Gateway как единая точка входа для авторизации
- Telegram Bot проходит ту же авторизационную цепочку
"""
