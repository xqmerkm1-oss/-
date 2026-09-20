import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN در فایل .env تنظیم نشده!")

if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID در فایل .env تنظیم نشده!")
