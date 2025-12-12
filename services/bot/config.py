# config.py

BOT_TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"

# Локальные файлы для bot_local
USER_TOKENS_PATH = "user_tokens.json"
USER_INFO_PATH = "user_info.json"
USER_STATES_PATH = "user_states.json"
APPLICATIONS_PATH = "applications.json"
EVENTS_PATH = "events.json"
PHOTOS_DIR = "photos"

# API Gateway
GATEWAY_URL = "http://localhost:8000"

# Сервисы, доступные через gateway
GATEWAY_SERVICES = {
    "auth": "auth",
    "users": "users",
    "events": "events",
    # при необходимости можно добавить:
    # "attendance": "attendance",
}
