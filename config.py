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

# ===== لینک افزودن ربات به گروه =====
ADD_TO_GROUP_LINK = "https://t.me/Kaskhelkhizbot?startgroup=true"

# ===== دیتابیس Postgres =====
DATABASE_URL = os.getenv("DATABASE_URL")

# ===== پوینت‌ها =====
KIR_POINT_REWARD = 5
KOS_POINT_REWARD = 5
WEAK_POINT_REWARD = 1
HIGH_POINT_REWARD = 1
TOP_POINT_REWARD = 1

KIR_POINT_COOLDOWN = 180      # ۳ دقیقه

# ===== کلمات کلیدی =====
KIR_WORD = "کیر"
KOS_WORD = "کص"
MALE_GOOD_WORD = "پسر خوب"
FEMALE_GOOD_WORD = "دختر خوب"
HIGH_WORD = "سلام گلم"
TOP_WORD = "کیک"

# ===== آستانه‌ها =====
HIGH_THRESHOLD = 50000
TOP_THRESHOLD = 200000

# ===== زمان انقضای راهنما (ثانیه) =====
HELP_EXPIRE_SECONDS = 300     # ۵ دقیقه

# ===== رتبه‌ها =====
# (حداقل پوینت، لقب)
MALE_RANKS = [
    (1500000, "👑 شومبول برتر"),
    (800000,  "🥇 کیر طلای"),
    (300000,  "🍆 مینی کیر"),
    (100000,  "🍌 شومبول"),
    (0,       "🆕 تازه‌وارد"),
]

FEMALE_RANKS = [
    (1500000, "👑 چوچول برتر"),
    (800000,  "🤍 سیفید"),
    (300000,  "🌸 چوچول"),
    (100000,  "🍑 مینی کص"),
    (0,       "🆕 تازه‌وارد"),
]


def get_rank(points: int, gender: str) -> str:
    """گرفتن لقب بر اساس پوینت و جنسیت"""
    if gender == "male_have":
        ranks = MALE_RANKS
    elif gender == "female_have":
        ranks = FEMALE_RANKS
    else:
        return "🆕 تازه‌وارد"

    for min_points, title in ranks:
        if points >= min_points:
            return title

    return "🆕 تازه‌وارد"


def get_next_rank(points: int, gender: str):
    """
    گرفتن رتبه بعدی و پوینت لازم
    Returns: (next_title, points_needed) یا (None, 0)
    """
    if gender == "male_have":
        ranks = sorted(MALE_RANKS, key=lambda x: x[0])
    elif gender == "female_have":
        ranks = sorted(FEMALE_RANKS, key=lambda x: x[0])
    else:
        return None, 0

    for min_points, title in ranks:
        if points < min_points:
            return title, min_points - points

    return None, 0
