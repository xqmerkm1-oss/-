from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن به گروه",
                url="https://t.me/Schompedbot?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton(
                "📢 کانال اطلاع رسانی",
                url="https://t.me/SchompedCanal",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
