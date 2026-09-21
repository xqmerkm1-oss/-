from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK, ADD_TO_GROUP_LINK


def joined_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های پیام بعد از تأیید جنسیت"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن ربات به گروه",
                url=ADD_TO_GROUP_LINK,
                api_kwargs={"style": "success"},
            ),
        ],
        [
            InlineKeyboardButton(
                "📖 راهنما",
                callback_data="show_help",
                api_kwargs={"style": "primary"},
            ),
        ],
    ])


def join_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های عضویت در کانال + تایید"""
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
    """۴ دکمه انتخاب جنسیت + جنبه"""
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
    """دکمه‌های تأیید نهایی"""
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


def help_keyboard(user_id: int, gender: str) -> InlineKeyboardMarkup:
    """کیبورد راهنما — شخصی‌سازی شده"""
    rows = []

    if gender == "male_have":
        rows.append([
            InlineKeyboardButton(
                "🍌 کیر پوینت",
                callback_data=f"help_kir_{user_id}",
                api_kwargs={"style": "success"},
            ),
        ])
    elif gender == "female_have":
        rows.append([
            InlineKeyboardButton(
                "🍑 کص پوینت",
                callback_data=f"help_kos_{user_id}",
                api_kwargs={"style": "success"},
            ),
        ])
    elif gender == "male_dont":
        rows.append([
            InlineKeyboardButton(
                "🌹 پسر خوب پوینت",
                callback_data=f"help_male_dont_{user_id}",
                api_kwargs={"style": "danger"},
            ),
        ])
    elif gender == "female_dont":
        rows.append([
            InlineKeyboardButton(
                "🌸 دختر خوب پوینت",
                callback_data=f"help_female_dont_{user_id}",
                api_kwargs={"style": "danger"},
            ),
        ])

    rows.append([
        InlineKeyboardButton(
            "📖 توضیحات بلند",
            callback_data=f"help_long_{user_id}",
            api_kwargs={"style": "primary"},
        ),
    ])

    rows.append([
        InlineKeyboardButton(
            "💰 پوینت من",
            callback_data=f"help_mypoints_{user_id}",
            api_kwargs={"style": "primary"},
        ),
    ])

    return InlineKeyboardMarkup(rows)


def help_back_keyboard(user_id: int, gender: str) -> InlineKeyboardMarkup:
    """دکمه برگشت به راهنما"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📖 توضیحات بلند",
                callback_data=f"help_long_{user_id}",
                api_kwargs={"style": "primary"},
            ),
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data=f"help_back_{user_id}",
                api_kwargs={"style": "success"},
            ),
        ]
    ])


def inactive_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های یادآوری عدم فعالیت"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💪 فعالیت می‌کنم",
                callback_data=f"inactive_stay_{user_id}",
                api_kwargs={"style": "success"},
            ),
        ],
        [
            InlineKeyboardButton(
                "🚶 سیکتیر بابا",
                callback_data=f"inactive_leave_{user_id}",
                api_kwargs={"style": "danger"},
            ),
        ],
    ])
