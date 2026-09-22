import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import help_keyboard, start_keyboard
from messages import HELP_TEXT, START_TEXT
from repository import (
    get_or_create_user,
    get_top_users,
    give_reward,
    seconds_remaining,
)

logger = logging.getLogger(__name__)


# 🎁 کلمات کلیدی: {کلمه: (پد, لقب)}
KEYWORDS: dict[str, tuple[int, str]] = {
    "گل رز": (10, "رزیتا 🌹"),
    "دختر خوب": (10, "دختر خوب 🌸"),
    "پسر خوب": (10, "پسر خوب 🌟"),
    "نان بربری": (5, "نانوا 🥖"),
    "نون بربری": (5, "نانوا 🥖"),
    "آجور": (3, "آجورخور 🥒"),
    "سیفید": (5, "سفیدبرفی ⚪"),
    "شومپد": (7, "شومپدی 🤖"),
}

# دستورات متنی (بدون اسلش)
CMD_HELP = "راهنما"
CMD_PROFILE = "پروفایل"
CMD_TOP = "برترها"


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return

    try:
        await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)

    await update.message.reply_text(
        START_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=help_keyboard(),
        disable_web_page_preview=True,
    )


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    try:
        db_user = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    remaining = seconds_remaining(db_user)
    if remaining > 0:
        minutes = remaining // 60
        secs = remaining % 60
        if minutes > 0 and secs > 0:
            cooldown = f"⏳ {minutes} دقیقه و {secs} ثانیه تا جایزه بعدی"
        elif minutes > 0:
            cooldown = f"⏳ {minutes} دقیقه تا جایزه بعدی"
        else:
            cooldown = f"⏳ {secs} ثانیه تا جایزه بعدی"
    else:
        cooldown = "✅ آماده‌ی گرفتن جایزه‌ای!"

    title = db_user.title or "بدون لقب"
    name = db_user.first_name or "دوست عزیز"

    await update.message.reply_text(
        f"👤 <b>پروفایل {name}</b>\n\n"
        f"💎 پدها: <b>{db_user.pads}</b>\n"
        f"🏆 لقب: <b>{title}</b>\n"
        f"{cooldown}\n\n"
        f"💡 برای گرفتن پد، یه کلمه‌ی کلیدی بنویس (مثلاً <b>گل رز</b>)",
        parse_mode=ParseMode.HTML,
    )


async def top_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    try:
        top_users = await get_top_users(10)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if not top_users:
        await update.message.reply_text("هنوز کسی پدی نگرفته! 🥲")
        return

    medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 7
    lines = ["🏆 <b>۱۰ نفر برتر شومپد</b>\n"]
    for i, u in enumerate(top_users):
        name = u.first_name or u.username or f"کاربر {u.telegram_id}"
        title = u.title or "بدون لقب"
        lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پد — {title}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """همه پیام‌های متنی رو بررسی می‌کنه: دستورات متنی + کلمات کلیدی."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if user is None:
        return

    # ─── دستورات متنی (بدون اسلش) ───
    if text == CMD_HELP:
        await help_handler(update, context)
        return
    if text == CMD_PROFILE:
        await profile_handler(update, context)
        return
    if text in (CMD_TOP, "برتر"):
        await top_handler(update, context)
        return

    # ─── 🎯 فقط پیام‌های تک‌کلمه‌ای جایزه می‌گیرن ───
    if " " in text or "\n" in text or "\t" in text:
        return

    # ─── چک کن آیا این تک‌کلمه، یکی از کلمات کلیدی هست ───
    matched: tuple[str, tuple[int, str]] | None = None
    for keyword, reward in KEYWORDS.items():
        if keyword == text:  # فقط تطابق کامل
            matched = (keyword, reward)
            break

    if matched is None:
        return

    keyword, (points, title) = matched

    # ─── گرفتن یا ساخت کاربر ───
    try:
        db_user = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    # ─── چک کردن کول‌داون ───
    remaining = seconds_remaining(db_user)
    if remaining > 0:
        minutes = remaining // 60
        secs = remaining % 60

        if minutes > 0 and secs > 0:
            wait_text = f"{minutes} دقیقه و {secs} ثانیه"
        elif minutes > 0:
            wait_text = f"{minutes} دقیقه"
        else:
            wait_text = f"{secs} ثانیه"

        await update.message.reply_text(
            f"😅 می‌بینم که خوشت اومده!\n\n"
            f"⏳ باید <b>{wait_text}</b> دیگه منتظر بمونی تا بتونی <b>{keyword}</b> بگیری!",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── دادن جایزه ───
    try:
        updated = await give_reward(user.id, points, title)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if updated is None:
        return

    await update.message.reply_text(
        f"🎉 <b>+{points} {keyword} پد گرفتی</b>\n\n"
        f"💎 پد هات : <b>{updated.pads}</b>\n"
        f"🏆 لقبت : <b>{title}</b>\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری",
        parse_mode=ParseMode.HTML,
    )
