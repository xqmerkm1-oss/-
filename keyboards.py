from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(
    text: str,
    url: str | None = None,
    callback_data: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    kwargs = {"text": text}
    if url is not None:
        kwargs["url"] = url
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if style is not None:
        try:
            return InlineKeyboardButton(**kwargs, style=style)
        except TypeError:
            return InlineKeyboardButton(**kwargs)
    return InlineKeyboardButton(**kwargs)


def start_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            _btn("➕ افزودن به گروه", url="https://t.me/Schompedbot?startgroup=true", style="success"),
            _btn("📢 کانال اطلاع رسانی", url="https://t.me/SchompedCanal", style="primary"),
        ],
        [
            _btn("👤 حساب من", callback_data="menu_profile", style="primary"),
            _btn("🛒 فروشگاه", callback_data="menu_shop", style="primary"),
        ],
        [
            _btn("🏆 برترها", callback_data="menu_top", style="success"),
            _btn("🎁 دعوت دوستان", callback_data="menu_invite", style="success"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("🔙 بازگشت", callback_data="menu_back", style="danger")],
    ])


def help_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های راهنمای اصلی — با owner_id برای قفل."""
    keyboard = [
        [
            _btn("📘 توضیحات کوتاه", callback_data=f"help_short_{owner_id}", style="primary"),
            _btn("📚 توضیحات کامل", callback_data=f"help_full_{owner_id}", style="success"),
        ],
        [
            _btn("🔙 بستن", callback_data=f"menu_close_{owner_id}", style="danger"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def help_back_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    """دکمه بازگشت به راهنمای اصلی — با owner_id."""
    keyboard = [
        [
            _btn("🔙 بازگشت به راهنما", callback_data=f"help_back_{owner_id}", style="primary"),
            _btn("❌ بستن", callback_data=f"menu_close_{owner_id}", style="danger"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def shop_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [_btn("🔪 خرید کارگر افغانی (۱۰۰ 🥖)", callback_data="shop_buy_worker", style="primary")],
        [_btn("🛡️ خرید لر (۵۰ 🧱)", callback_data="shop_buy_lord", style="primary")],
        [_btn("🍰 خرید کیک یزدی (۱۰ 🥖)", callback_data="shop_buy_cake", style="primary")],
        [_btn("🔙 بازگشت", callback_data="menu_back", style="danger")],
    ]
    return InlineKeyboardMarkup(keyboard)
