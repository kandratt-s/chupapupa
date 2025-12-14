from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "photos"

EVENT_PHOTOS = PHOTOS_DIR / "events"
PROFILE_PHOTOS = PHOTOS_DIR / "profiles"

for p in [EVENT_PHOTOS, PROFILE_PHOTOS]:
    p.mkdir(parents=True, exist_ok=True)