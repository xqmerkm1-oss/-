from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK


def join_keyboard() -> InlineKeyboardMarkup:
    """دکمههای عضویت در کانال + تایید"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 کانال کصخل خیز", url=CHANNEL_LINK),
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_join"),
        ]
    ])


def gender_keyboard() -> InlineKeyboardMarkup:
    """دکمههای انتخاب جنسیت"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👦 پسر", callback_data="gender_male"),
            InlineKeyboardButton("👧 دختر", callback_data="gender_female"),
        ]
    ])
