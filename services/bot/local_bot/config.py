# config.py

BOT_TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"

# Локальные файлы для bot_local
DATA_DIR = "services/bot/local_bot/data"

USER_TOKENS_PATH = f"{DATA_DIR}/user_tokens.json"
USER_INFO_PATH = f"{DATA_DIR}/user_info.json"
USER_STATES_PATH = f"{DATA_DIR}/user_states.json"
APPLICATIONS_PATH = f"{DATA_DIR}/applications.json"
EVENTS_PATH = f"{DATA_DIR}/events.json"

PHOTOS_DIR = "services/bot/local_bot/photos"

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
