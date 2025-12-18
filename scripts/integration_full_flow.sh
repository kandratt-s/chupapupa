#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
PYTHON_BIN="${PYTHON_BIN:-}"

# Pick a Python interpreter that really works (avoid broken Windows shims).
pick_python() {
  local candidates=()
  if [[ -n "$PYTHON_BIN" ]]; then
    candidates=("$PYTHON_BIN")
  else
    candidates=("python3" "python" "py -3" "py")
  fi
  for cand in "${candidates[@]}"; do
    # Split string into array to allow values like "py -3"
    # shellcheck disable=SC2206
    local cmd=($cand)
    if "${cmd[@]}" - <<'PY' >/dev/null 2>&1
print("ok")
PY
    then
      PY_CMD=("${cmd[@]}")
      return 0
    fi
  done
  echo "Python interpreter not found (tried python3/python/py). Install Python or set PYTHON_BIN" >&2
  exit 1
}

pick_python

run_python() {
  "${PY_CMD[@]}" "$@"
}

# Credentials and files (override via env if нужно)
ADMIN_PASS="${ADMIN_PASS:-admin-pass-123}"
USER_PASS="${USER_PASS:-user-pass-123}"
ADMIN_PHOTO="${ADMIN_PHOTO:-$(pwd)/new_test_user.jpg}"
USER_PHOTO="${USER_PHOTO:-$(pwd)/test_user.jpg}"
ATT_PHOTO="${ATT_PHOTO:-$(pwd)/attendance_photo.jpg}"

ts="$(date +%s)"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin_${ts}@example.com}"
USER_EMAIL="${USER_EMAIL:-user_${ts}@example.com}"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "File not found: $1" >&2
    exit 1
  fi
}

require_file "$ADMIN_PHOTO"
require_file "$USER_PHOTO"
require_file "$ATT_PHOTO"

# Convert path to Windows style if cygpath is available (fixes curl on Git Bash/Windows)
to_curl_path() {
  local p="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$p"
  else
    printf '%s' "$p"
  fi
}

ADMIN_PHOTO_CURL="$(to_curl_path "$ADMIN_PHOTO")"
USER_PHOTO_CURL="$(to_curl_path "$USER_PHOTO")"
ATT_PHOTO_CURL="$(to_curl_path "$ATT_PHOTO")"

wait_for_ready() {
  local url="$1" timeout="${2:-90}" elapsed=0
  echo "Ожидаю готовность API ($url) ..."
  while ! curl -fs "$url" >/dev/null 2>&1; do
    sleep 2
    elapsed=$((elapsed+2))
    if (( elapsed >= timeout )); then
      echo "Не дождался готовности за ${timeout}s ($url)" >&2
      exit 1
    fi
  done
}

json_get() {
  local key="$1"
  if [[ -n "${JSON_DATA:-}" ]]; then
    run_python - "$key" <<'PY'
import json, sys, os
key = sys.argv[1]
raw = os.environ.get("JSON_DATA", "")
data = json.loads(raw)
val = data
for part in key.split('.'):
    val = val[part]
print(val)
PY
  else
    run_python - "$key" <<'PY'
import json, sys
key = sys.argv[1]
data = json.load(sys.stdin)
val = data
for part in key.split('.'):
    val = val[part]
print(val)
PY
  fi
}

wait_for_ready "$BASE/health"

echo "1) Регистрация админа..."
admin_resp="$(curl -sS -f -X POST "$BASE/user-statistics/users/register" \
  -F "first_name=Admin" \
  -F "last_name=Test" \
  -F "group_name=INT-01" \
  -F "hse_email=$ADMIN_EMAIL" \
  -F "password=$ADMIN_PASS" \
  -F "photo=@${ADMIN_PHOTO_CURL};type=image/jpeg")"
echo "   response: $admin_resp"
ADMIN_ID="$(JSON_DATA="$admin_resp" json_get user_id)"
echo "   admin_id=$ADMIN_ID email=$ADMIN_EMAIL"

echo "2) Логин админа и повышение роли..."
admin_login="$(curl -sS -f -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":$ADMIN_ID,\"password\":\"$ADMIN_PASS\"}")"
ADMIN_TOKEN="$(JSON_DATA="$admin_login" json_get access_token)"

curl -sS -f -X PUT "$BASE/auth/$ADMIN_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}' >/dev/null

# Обновляем токен с ролью admin
admin_login="$(curl -sS -f -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":$ADMIN_ID,\"password\":\"$ADMIN_PASS\"}")"
ADMIN_TOKEN="$(JSON_DATA="$admin_login" json_get access_token)"
echo "   admin token получен"

echo "3) Регистрация пользователя..."
user_resp="$(curl -sS -f -X POST "$BASE/user-statistics/users/register" \
  -F "first_name=User" \
  -F "last_name=Test" \
  -F "group_name=INT-01" \
  -F "hse_email=$USER_EMAIL" \
  -F "password=$USER_PASS" \
  -F "photo=@${USER_PHOTO_CURL};type=image/jpeg")"
echo "   response: $user_resp"
USER_ID="$(JSON_DATA="$user_resp" json_get user_id)"
echo "   user_id=$USER_ID email=$USER_EMAIL"

echo "4) Логин пользователя..."
user_login="$(curl -sS -f -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":$USER_ID,\"password\":\"$USER_PASS\"}")"
USER_TOKEN="$(JSON_DATA="$user_login" json_get access_token)"

echo "5) Создание события (админ)..."
event_resp="$(curl -sS -f -X POST "$BASE/events/admin/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Integration test","date":"2025-12-20T18:00:00Z","profilnoe":false,"opisanie":"Test event","active":true}')"
EVENT_ID="$(JSON_DATA="$event_resp" json_get event_id)"
echo "   event_id=$EVENT_ID"

echo "6) Заявка (пользователь)..."
att_resp="$(curl -sS -f -X POST "$BASE/attendances/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "event_id=$EVENT_ID" \
  -F "notes=My attendance" \
  -F "photo=@${ATT_PHOTO_CURL};type=image/jpeg")"
ATT_ID="$(JSON_DATA="$att_resp" json_get attendance_id)"
echo "   attendance_id=$ATT_ID"

echo "7) Проверка пользователя..."
user_data="$(curl -s -H "Authorization: Bearer $USER_TOKEN" "$BASE/user-statistics/users/me")"
echo "$user_data" | run_python -m json.tool
USER_PHOTO_PATH="$(JSON_DATA="$user_data" json_get photo_path | sed 's|/shared/photos/||')"

echo "8) Проверка заявки..."
att_data="$(curl -s -H "Authorization: Bearer $USER_TOKEN" "$BASE/attendances/$ATT_ID")"
echo "$att_data" | run_python -m json.tool
ATT_FILE_PATH="$(JSON_DATA="$att_data" json_get file_path | sed 's|photos/||')"

echo "9) Проверка доступности фото пользователя..."
if [[ -n "$USER_PHOTO_PATH" ]]; then
    photo_url="$BASE/photos/$USER_PHOTO_PATH"
    if curl -f -I "$photo_url" >/dev/null 2>&1; then
        echo "   ✅ Фото пользователя доступно: $photo_url"
    else
        echo "   ❌ Фото пользователя недоступно: $photo_url" >&2
        exit 1
    fi
else
    echo "   ⚠️  Фото пользователя не указано"
fi

echo "10) Проверка доступности фото заявки..."
if [[ -n "$ATT_FILE_PATH" ]]; then
    photo_url="$BASE/photos/$ATT_FILE_PATH"
    if curl -f -I "$photo_url" >/dev/null 2>&1; then
        echo "   ✅ Фото заявки доступно: $photo_url"
    else
        echo "   ❌ Фото заявки недоступно: $photo_url" >&2
        exit 1
    fi
else
    echo "   ⚠️  Фото заявки не указано"
fi

echo "9) Скачивание фото..."
echo "   Скачиваем фото админа..."
curl -s "$BASE/photos/faces/$ADMIN_ID.jpg" -o "downloaded_admin_face.jpg"
echo "   Скачиваем фото пользователя..."
curl -s "$BASE/photos/faces/$USER_ID.jpg" -o "downloaded_user_face.jpg"
echo "   Скачиваем фото attendance..."
curl -s "$BASE/photos/attendances/$ATT_ID.jpg" -o "downloaded_attendance.jpg"

echo "   Проверяем скачанные файлы:"
if ls -la downloaded_*.jpg 2>/dev/null; then
    echo "   ✅ Все файлы скачаны успешно"
    # Проверяем, что файлы являются изображениями
    for file in downloaded_*.jpg; do
        if file "$file" | grep -q "JPEG image"; then
            echo "   ✅ $file - корректное JPEG изображение"
        else
            echo "   ❌ $file - не является JPEG изображением"
            cat "$file"
        fi
    done
else
    echo "   ❌ Ошибка: файлы не найдены"
    exit 1
fi

echo "✅ Готово"
