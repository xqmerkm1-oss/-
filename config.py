import os
from dotenv import load_dotenv

load_dotenv()

# ===== مقادیر پیشفرض =====
# این مقادیر اگه توی Variables نبودن، از اینجا استفاده میشن
DEFAULT_BOT_TOKEN = "8845091304:AAGSunCBF1Ijfgyn_do2xjHyUxwjR_fWKpA"
DEFAULT_CHANNEL_ID = "-1004344839671"
DEFAULT_CHANNEL_LINK = "https://t.me/Afirstratescumbag"
DEFAULT_DATABASE_PATH = "data/bot.db"

# ===== خواندن از محیط یا پیشفرض =====
BOT_TOKEN = os.getenv("BOT_TOKEN") or DEFAULT_BOT_TOKEN
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or DEFAULT_CHANNEL_ID)
CHANNEL_LINK = os.getenv("CHANNEL_LINK") or DEFAULT_CHANNEL_LINK
DATABASE_PATH = os.getenv("DATABASE_PATH") or DEFAULT_DATABASE_PATH
