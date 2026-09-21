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

# ===== امتیازها =====
KIR_POINT_REWARD = 5          # پسر با جنبه — کیر
KOS_POINT_REWARD = 5          # دختر با جنبه — کص
WEAK_POINT_REWARD = 1         # بی‌جنبه‌ها — پسر خوب / دختر خوب
HIGH_POINT_REWARD = 1         # بالای ۵۰۰۰۰ — سلام گلم
TOP_POINT_REWARD = 1          # بالای ۲۰۰۰۰۰ — کیک

KIR_POINT_COOLDOWN = 180      # ۳ دقیقه
KOS_POINT_COOLDOWN = 180
WEAK_POINT_COOLDOWN = 180
HIGH_POINT_COOLDOWN = 180
TOP_POINT_COOLDOWN = 180

# ===== کلمات کلیدی =====
KIR_WORD = "کیر"
KOS_WORD = "کص"
MALE_GOOD_WORD = "پسر خوب"     # برای پسر بی‌جنبه
FEMALE_GOOD_WORD = "دختر خوب"  # برای دختر بی‌جنبه
HIGH_WORD = "سلام گلم"          # بالای ۵۰۰۰۰
TOP_WORD = "کیک"               # بالای ۲۰۰۰۰۰

# ===== آستانه‌ها =====
HIGH_THRESHOLD = 50000
TOP_THRESHOLD = 200000
