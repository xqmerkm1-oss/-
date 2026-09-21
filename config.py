import os
from dotenv import load_dotenv

load_dotenv()

# ===== مقادیر پیشفرض =====
DEFAULT_BOT_TOKEN = "8979774904:AAHWGxVXyfpnglyeL7Gj8ldLPH2yCkKdThE"
DEFAULT_CHANNEL_ID = "-1004372622419"
DEFAULT_CHANNEL_LINK = "https://t.me/Kaskhelkhiz"

BOT_TOKEN = os.getenv("BOT_TOKEN") or DEFAULT_BOT_TOKEN
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or DEFAULT_CHANNEL_ID)
CHANNEL_LINK = os.getenv("CHANNEL_LINK") or DEFAULT_CHANNEL_LINK

# ===== دیتابیس Postgres =====
DATABASE_URL = os.getenv("DATABASE_URL")

# ===== کیر پوینت =====
KIR_POINT_REWARD = 5          # امتیاز هر بار
KIR_POINT_COOLDOWN = 180      # ثانیه (۳ دقیقه)
KIR_WORD = "کیر"              # کلمه‌ای که امتیاز میده
