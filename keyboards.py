from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن به گروه",
                url="https://t.me/Schompedbot?startgroup=true",
                style="success",  # 🟢 سبز
            )
        ],
        [
            InlineKeyboardButton(
                "📢 کانال اطلاع رسانی",
                url="https://t.me/SchompedCanal",
                style="primary",  # 🔵 آبی
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
