import logging
import random

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import start_keyboard
from messages import HELP_TEXT, START_TEXT
from repository import (
    add_score_and_title,
    get_or_create_user,
    is_on_cooldown,
    set_cooldown,
)

logger = logging.getLogger(__name__)


# 🎁 لیست کلمات کلیدی و جایزه‌هاشون
KEYWORD_REWARDS: dict[str, tuple[int, list[str]]] = {
    "دختر خوب": (10, [
        "دختر خوب ماه 🌸",
        "قلب طلایی 💛",
        "شاهزاده خانم 👑",
        "ملکه مهربونی 💐",
    ]),
    "پسر خوب": (10, [
        "پسر خوب ماه 🌟",
        "آقای محترم 🎩",
        "جوانمرد 🦁",
        "سلطان ادب 👑",
    ]),
    "نان بربری": (5, [
        "نانوای حرفه‌ای 🥖",
        "سلطان نان 🍞",
        "بربری‌پز استاد 🥯",
    ]),
    "نون بربری": (5, [
        "نانوای حرفه‌ای 🥖",
        "سلطان نان 🍞",
        "بربری‌پز استاد 🥯",
    ]),
    "آجور": (3, [
        "آجور‌خور حرفه‌ای 🥒",
        "استاد آجور 🥬",
        "خیار‌شناس 🧪",
    ]),
    "گل رز": (7, [
        "گل‌فروش عاشق 🌹",
        "رز سیاه 🖤",
        "شاهزاده گل‌ها 🌷",
    ]),
}


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return

    try:
        await get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
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
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def keyword_reward_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """اگه کاربر یکی از کلمات کلیدی رو بفرسته، امتیاز و لقب می‌گیره."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user = update.effective_user
    if user is None:
        return

    # پیدا کردن اولین کلمه کلیدی مطابق
    matched: tuple[str, tuple[int, list[str]]] | None = None
    for keyword, reward in KEYWORD_REWARDS.items():
        if keyword in text:
            matched = (keyword, reward)
            break

    if matched is None:
        return

    keyword, (points, titles) = matched

    # ضد اسپم
    if is_on_cooldown(user.id):
        return

    # ساخت/گرفتن کاربر
    try:
        db_user = await get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    title = random.choice(titles)

    # آپدیت امتیاز و لقب
    try:
        await add_score_and_title(user.id, points, title)
    except Exception as exc:
        logger.exception("DB error (add_score): %s", exc)
        return

    set_cooldown(user.id)

    await update.message.reply_text(
        f"🎉 <b>{user.first_name}</b> عزیز!\n\n"
        f"✅ کلمه کلیدی: <b>{keyword}</b>\n"
        f"⭐ امتیاز دریافتی: <b>+{points}</b>\n"
        f"🏅 لقب جدید: <b>{title}</b>\n\n"
        f"💰 مجموع امتیاز: <b>{db_user.score + points}</b>",
        parse_mode=ParseMode.HTML,
    )
