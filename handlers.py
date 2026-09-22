import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import back_keyboard, help_keyboard, start_keyboard
from messages import HELP_TEXT, START_TEXT
from repository import (
    get_or_create_user,
    get_top_users,
    give_reward,
    seconds_remaining,
)

logger = logging.getLogger(__name__)


# 🎯 آی‌دی کانال عضویت اجباری
CHANNEL_ID = -1004372622419
CHANNEL_LINK = "https://t.me/SchompedCanal"


# 🎁 کلمات کلیدی: {کلمه: (پوینت, لقب)}
KEYWORDS: dict[str, tuple[int, str]] = {
    "گل رز": (10, "رزیتا 🌹"),
    "دختر خوب": (10, "دختر خوب 🌸"),
    "پسر خوب": (10, "پسر خوب 🌟"),
    "نون بربری": (5, "نانوا 🥖"),
    "آجور": (3, "آجورخور 🧱"),
    "سیفید": (5, "سفیدبرفی ⚪"),
    "شومپد": (7, "شومپدی 🤖"),
    "شمع": (5, "شمع‌ساز 🕯️"),
}

CMD_HELP = "راهنما"
CMD_PROFILE = "پروفایل"
CMD_TOP = "برترها"


async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """چک می‌کنه کاربر واقعاً عضو کانال هست یا نه."""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = member.status
        if status in ("member", "administrator", "creator"):
            return True
        return False
    except Exception as exc:
        logger.exception("get_chat_member error: %s", exc)
        return True


def join_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK, style="primary")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership", style="success")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return

    if not await is_user_member(context, user.id):
        await update.message.reply_text(
            "🔒 <b>برای استفاده از ربات شومپد، اول باید توی کانال ما عضو بشی!</b>\n\n"
            "📢 روی دکمه زیر بزن و عضو شو، بعد روی «✅ عضو شدم» بزن:",
            parse_mode=ParseMode.HTML,
            reply_markup=join_keyboard(),
        )
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


# ─────────────────────────────────────────────
# عضویت اجباری
# ─────────────────────────────────────────────
async def check_membership_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if query is None:
        return

    user = query.from_user
    if user is None:
        await query.answer()
        return

    if not await is_user_member(context, user.id):
        await query.answer(
            "😤 کوندبازی در نیار یارو!\n\n"
            "اول برو توی کانال عضو شو، بعد دوباره روی «✅ عضو شدم» بزن.",
            show_alert=True,
        )
        return

    await query.answer("✅ عضویتت تایید شد!")

    try:
        await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)

    await query.edit_message_text(
        START_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


# ─────────────────────────────────────────────
# دکمه‌های منوی اصلی
# ─────────────────────────────────────────────
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر همه دکمه‌های callback_data که با menu_ شروع می‌شن."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    user = query.from_user
    if user is None:
        return

    data = query.data  # menu_profile, menu_shop, menu_top, menu_invite, menu_back

    # ─── بازگشت به منوی اصلی ───
    if data == "menu_back":
        await query.edit_message_text(
            START_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(),
            disable_web_page_preview=True,
        )
        return

    # ─── حساب من ───
    if data == "menu_profile":
        try:
            db_user = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا در دریافت اطلاعات.", reply_markup=back_keyboard())
            return

        remaining = seconds_remaining(db_user)
        if remaining > 0:
            minutes = remaining // 60
            secs = remaining % 60
            if minutes > 0 and secs > 0:
                cooldown = f"⏳ {minutes} دقیقه و {secs} ثانیه"
            elif minutes > 0:
                cooldown = f"⏳ {minutes} دقیقه"
            else:
                cooldown = f"⏳ {secs} ثانیه"
        else:
            cooldown = "✅ آماده"

        username = f"@{db_user.username}" if db_user.username else "ندارد"
        title = db_user.title or "بدون لقب"
        name = db_user.first_name or "دوست عزیز"

        await query.edit_message_text(
            f"👤 <b>حساب من</b>\n\n"
            f"📛 نام: <b>{name}</b>\n"
            f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
            f"🔗 یوزرنیم: <b>{username}</b>\n"
            f"💎 پوینت‌ها: <b>{db_user.pads}</b>\n"
            f"🏆 لقب: <b>{title}</b>\n"
            f"⏳ وضعیت جایزه: {cooldown}\n\n"
            f"📅 عضویت از: <b>{db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else '---'}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── فروشگاه ───
    if data == "menu_shop":
        await query.edit_message_text(
            "🛒 <b>فروشگاه شومپد</b>\n\n"
            "🚧 این بخش در حال ساخته شدنه!\n\n"
            "به‌زودی می‌تونی با پوینت‌هات آیتم بخری و قوی‌تر بشی. 💪",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── برترها ───
    if data == "menu_top":
        try:
            top_users = await get_top_users(10)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا در دریافت اطلاعات.", reply_markup=back_keyboard())
            return

        if not top_users:
            await query.edit_message_text(
                "🏆 هنوز کسی پدی نگرفته! 🥲",
                reply_markup=back_keyboard(),
            )
            return

        medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 7
        lines = ["🏆 <b>۱۰ نفر برتر شومپد</b>\n"]
        for i, u in enumerate(top_users):
            name = u.first_name or u.username or f"کاربر {u.telegram_id}"
            title = u.title or "بدون لقب"
            lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پوینت — {title}")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── دعوت دوستان ───
    if data == "menu_invite":
        await query.edit_message_text(
            "🎁 <b>دعوت دوستان</b>\n\n"
            "🚧 این بخش در حال ساخته شدنه!\n\n"
            "به‌زودی می‌تونی دوستات رو دعوت کنی و پوینت جایزه بگیری. 🎉",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return


# ─────────────────────────────────────────────
# راهنما، پروفایل، برترها (دستور متنی)
# ─────────────────────────────────────────────
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
    username = f"@{db_user.username}" if db_user.username else "ندارد"

    await update.message.reply_text(
        f"👤 <b>حساب من</b>\n\n"
        f"📛 نام: <b>{name}</b>\n"
        f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
        f"🔗 یوزرنیم: <b>{username}</b>\n"
        f"💎 پوینت‌ها: <b>{db_user.pads}</b>\n"
        f"🏆 لقب: <b>{title}</b>\n"
        f"⏳ وضعیت: {cooldown}",
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
        lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پوینت — {title}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
# کلمات کلیدی و دستورات متنی
# ─────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if user is None:
        return

    if text == CMD_HELP:
        await help_handler(update, context)
        return
    if text == CMD_PROFILE:
        await profile_handler(update, context)
        return
    if text in (CMD_TOP, "برتر"):
        await top_handler(update, context)
        return

    if " " in text or "\n" in text or "\t" in text:
        return

    matched: tuple[str, tuple[int, str]] | None = None
    for keyword, reward in KEYWORDS.items():
        if keyword == text:
            matched = (keyword, reward)
            break

    if matched is None:
        return

    keyword, (points, title) = matched

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

    try:
        updated = await give_reward(user.id, points, title)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if updated is None:
        return

    await update.message.reply_text(
        f"🎉 <b>{points} {keyword} پوینت گرفتی</b>\n\n"
        f"💎 پد هات : <b>{updated.pads}</b>\n"
        f"🏆 لقبت : <b>{title}</b>\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری",
        parse_mode=ParseMode.HTML,
    )
