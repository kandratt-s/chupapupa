import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")

USER_TOKENS_PATH = os.path.join(DATA_DIR, "user_tokens.json")
USER_INFO_PATH = os.path.join(DATA_DIR, "user_info.json")
USER_STATES_PATH = os.path.join(DATA_DIR, "user_states.json")
APPLICATIONS_PATH = os.path.join(DATA_DIR, "applications.json")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")

PHOTOS_DIR = os.path.join(BASE_DIR, "photos")

GATEWAY_URL = "http://localhost:8000"

GATEWAY_SERVICES = {
    "auth": "auth",
    "users": "users",
    "events": "events",
}