import os

# Абсолютный путь к директории web/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Папка data внутри web/
DATA_DIR = os.path.join(BASE_DIR, "data")

# Пути к JSON-файлам
USERS_PATH = os.path.join(DATA_DIR, "users.json")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
APPLICATIONS_PATH = os.path.join(DATA_DIR, "applications.json")
