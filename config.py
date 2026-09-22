import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "8900397795:AAGcpe7E-qavZYXmIJlHsD4s9Li5_VkM2_8",
)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN تنظیم نشده.")
