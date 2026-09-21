from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK


def join_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های عضویت در کانال + تایید (رنگی)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 کانال کصخل خیز",
                url=CHANNEL_LINK,
                api_kwargs={"style": "primary"},
            ),
            InlineKeyboardButton(
                "✅ عضو شدم",
                callback_data="check_join",
                api_kwargs={"style": "success"},
            ),
        ]
    ])


def gender_keyboard() -> InlineKeyboardMarkup:
    """۴ دکمه انتخاب جنسیت + جنبه (سبز/قرمز)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💁‍♀ دخترم جنبه دارم",
                callback_data="gender_female_have",
                api_kwargs={"style": "success"},
            ),
            InlineKeyboardButton(
                "🙅‍♀ دخترم جنبه ندارم",
                callback_data="gender_female_dont",
                api_kwargs={"style": "danger"},
            ),
        ],
        [
            InlineKeyboardButton(
                "🙋‍♂ پسرم جنبه دارم",
                callback_data="gender_male_have",
                api_kwargs={"style": "success"},
            ),
            InlineKeyboardButton(
                "🙆‍♂ پسرم جنبه ندارم",
                callback_data="gender_male_dont",
                api_kwargs={"style": "danger"},
            ),
        ],
    ])


def confirm_keyboard(gender_value: str) -> InlineKeyboardMarkup:
    """دکمه‌های تأیید نهایی — «مطمئنم» و «مطمئن نیستم»"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ مطمئنم",
                callback_data=f"confirm_{gender_value}",
                api_kwargs={"style": "success"},
            ),
            InlineKeyboardButton(
                "❌ مطمئن نیستم",
                callback_data=f"cancel_{gender_value}",
                api_kwargs={"style": "danger"},
            ),
        ]
    ])
