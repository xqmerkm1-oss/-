from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK


def join_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های عضویت در کانال + تایید"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 کانال کصخل خیز", url=CHANNEL_LINK),
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_join"),
        ]
    ])


def gender_keyboard() -> InlineKeyboardMarkup:
    """۴ دکمه انتخاب جنسیت + جنبه (سبز/قرمز)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💁‍♀ دخترم جنبه دارم",
                callback_data="gender_female_have",
                api_kwargs={"style": "success"},  # 🟢 سبز
            ),
            InlineKeyboardButton(
                "🙅‍♀ دخترم جنبه ندارم",
                callback_data="gender_female_dont",
                api_kwargs={"style": "danger"},  # 🔴 قرمز
            ),
        ],
        [
            InlineKeyboardButton(
                "🙋‍♂ پسرم جنبه دارم",
                callback_data="gender_male_have",
                api_kwargs={"style": "success"},  # 🟢 سبز
            ),
            InlineKeyboardButton(
                "🙆‍♂ پسرم جنبه ندارم",
                callback_data="gender_male_dont",
                api_kwargs={"style": "danger"},  # 🔴 قرمز
            ),
        ],
    ])
