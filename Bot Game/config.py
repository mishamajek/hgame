import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

WINDOWS_CHANNEL_ID = int(os.getenv("WINDOWS_CHANNEL_ID", "-1001234567890"))
ANDROID_CHANNEL_ID = int(os.getenv("ANDROID_CHANNEL_ID", "-1001234567891"))

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"

GAMES_PER_PAGE = 5
COMMENTS_PER_PAGE = 5

PLATFORMS = {
    "windows": {"display": "💻 Windows", "channel_id": WINDOWS_CHANNEL_ID},
    "android": {"display": "📱 Android", "channel_id": ANDROID_CHANNEL_ID}
}

LOGS_DIR.mkdir(exist_ok=True)