import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://shomped:shomped@localhost:5432/shomped",
)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN در متغیرهای محیطی تنظیم نشده است.")
