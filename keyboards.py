from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, url: str, style: str | None = None) -> InlineKeyboardButton:
    kwargs = {"text": text, "url": url}
    if style is not None:
        try:
            return InlineKeyboardButton(**kwargs, style=style)
        except TypeError:
            return InlineKeyboardButton(**kwargs)
    return InlineKeyboardButton(**kwargs)


def start_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            _btn(
                "➕ افزودن به گروه",
                "https://t.me/Schompedbot?startgroup=true",
                style="success",
            )
        ],
        [
            _btn(
                "📢 کانال اطلاع رسانی",
                "https://t.me/SchompedCanal",
                style="primary",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def help_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            _btn(
                "➕ افزودن به گروه",
                "https://t.me/Schompedbot?startgroup=true",
                style="success",
            ),
            _btn(
                "📢 کانال اطلاع رسانی",
                "https://t.me/SchompedCanal",
                style="primary",
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
