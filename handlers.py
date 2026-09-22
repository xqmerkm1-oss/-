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
    mark_bread_used,
    seconds_remaining,
)

logger = logging.getLogger(__name__)


CHANNEL_ID = -1004372622419
CHANNEL_LINK = "https://t.me/SchompedCanal"


# 🎁 کلمات کلیدی: {کلمه: (پد, حداقل پد)}
KEYWORDS: dict[str, tuple[int, int]] = {
    "گل رز": (2, 0),
    "دختر خوب": (5, 500),
    "پسر خوب": (5, 500),
    "نون بربری": (5, 1000),
    "آجر": (5, 3000),
    "شمع": (5, 6000),
    "سیفید": (5, 10000),
    "شومپد": (10, 20000),
}

CMD_HELP = "راهنما"
CMD_PROFILE = "پروفایل"
CMD_TOP = "برترها"


async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
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


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    user = query.from_user
    if user is None:
        return

    data = query.data

    if data == "menu_back":
        await query.edit_message_text(
            START_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(),
            disable_web_page_preview=True,
        )
        return

    if data == "menu_close":
        try:
            await query.message.delete()
        except Exception as exc:
            logger.exception("Delete error: %s", exc)
        return

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
        name = db_user.first_name or "دوست عزیز"

        if db_user.pads >= 20000:
            unlock_status = "✅ همه کلمات باز شده!"
        elif db_user.pads >= 10000:
            unlock_status = "✅ <b>سیفید</b> باز شده!"
        elif db_user.pads >= 6000:
            unlock_status = "✅ <b>شمع</b> باز شده!"
        elif db_user.pads >= 3000:
            unlock_status = "✅ <b>آجر</b> باز شده!"
        elif db_user.pads >= 1000:
            unlock_status = "✅ <b>نون بربری</b> باز شده!"
        elif db_user.pads >= 500:
            unlock_status = "✅ <b>دختر خوب</b> و <b>پسر خوب</b> باز شده!"
        else:
            needed = 500 - db_user.pads
            unlock_status = f"🔒 {needed} پد دیگه تا باز شدن <b>دختر خوب</b> و <b>پسر خوب</b>"

        bread_status = ""
        if db_user.bread_used:
            bread_status = "\n⚠️ چون <b>نون بربری</b> زدی، <b>دختر خوب</b> و <b>پسر خوب</b> برات قفل شده!"

        await query.edit_message_text(
            f"👤 <b>حساب من</b>\n\n"
            f"📛 نام: <b>{name}</b>\n"
            f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
            f"🔗 یوزرنیم: <b>{username}</b>\n"
            f"💎 پدها: <b>{db_user.pads}</b>\n"
            f"⏳ وضعیت جایزه: {cooldown}\n\n"
            f"{unlock_status}{bread_status}\n\n"
            f"📅 عضویت از: <b>{db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else '---'}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    if data == "menu_shop":
        await query.edit_message_text(
            "🛒 <b>فروشگاه شومپد</b>\n\n"
            "🚧 این بخش در حال ساخته شدنه!\n\n"
            "به‌زودی می‌تونی با پدهات آیتم بخری و قوی‌تر بشی. 💪",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

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
            lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پد")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    if data == "menu_invite":
        await query.edit_message_text(
            "🎁 <b>دعوت دوستان</b>\n\n"
            "🚧 این بخش در حال ساخته شدنه!\n\n"
            "به‌زودی می‌تونی دوستات رو دعوت کنی و پد جایزه بگیری. 🎉",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return


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

    name = db_user.first_name or "دوست عزیز"
    username = f"@{db_user.username}" if db_user.username else "ندارد"

    if db_user.pads >= 20000:
        unlock_status = "✅ همه کلمات باز شده!"
    elif db_user.pads >= 10000:
        unlock_status = "✅ <b>سیفید</b> باز شده!"
    elif db_user.pads >= 6000:
        unlock_status = "✅ <b>شمع</b> باز شده!"
    elif db_user.pads >= 3000:
        unlock_status = "✅ <b>آجر</b> باز شده!"
    elif db_user.pads >= 1000:
        unlock_status = "✅ <b>نون بربری</b> باز شده!"
    elif db_user.pads >= 500:
        unlock_status = "✅ <b>دختر خوب</b> و <b>پسر خوب</b> باز شده!"
    else:
        needed = 500 - db_user.pads
        unlock_status = f"🔒 {needed} پد دیگه تا باز شدن <b>دختر خوب</b> و <b>پسر خوب</b>"

    bread_status = ""
    if db_user.bread_used:
        bread_status = "\n⚠️ چون <b>نون بربری</b> زدی، <b>دختر خوب</b> و <b>پسر خوب</b> برات قفل شده!"

    await update.message.reply_text(
        f"👤 <b>حساب من</b>\n\n"
        f"📛 نام: <b>{name}</b>\n"
        f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
        f"🔗 یوزرنیم: <b>{username}</b>\n"
        f"💎 پدها: <b>{db_user.pads}</b>\n"
        f"⏳ وضعیت: {cooldown}\n\n"
        f"{unlock_status}{bread_status}",
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
        lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پد")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


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

    if text not in KEYWORDS:
        return

    points, required_pads = KEYWORDS[text]

    try:
        db_user = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if text in ("دختر خوب", "پسر خوب") and db_user.bread_used:
        await update.message.reply_text(
            "🔒 چون <b>نون بربری</b> زدی، دیگه نمی‌تونی <b>دختر خوب</b> و <b>پسر خوب</b> بزنی!",
            parse_mode=ParseMode.HTML,
        )
        return

    if db_user.pads < required_pads:
        needed = required_pads - db_user.pads
        await update.message.reply_text(
            f"🔒 <b>{text}</b> هنوز برات باز نشده!\n\n"
            f"💎 پدهای فعلی: <b>{db_user.pads}</b>\n"
            f"🎯 برای باز شدن <b>{text}</b>، باید حداقل <b>{required_pads}</b> پد داشته باشی.\n\n"
            f"📉 <b>{needed} پد</b> دیگه لازم داری.\n\n"
            f"💡 فقط با <b>گل رز</b> (۲ پد) می‌تونی پد جمع کنی!",
            parse_mode=ParseMode.HTML,
        )
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
            f"⏳ باید <b>{wait_text}</b> دیگه منتظر بمونی تا بتونی <b>{text}</b> بگیری!",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        updated = await give_reward(user.id, points)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if updated is None:
        return

    bread_msg = ""
    if text == "نون بربری":
        try:
            await mark_bread_used(user.id)
            bread_msg = "\n\n⚠️ از این به بعد <b>دختر خوب</b> و <b>پسر خوب</b> برات قفل شده!"
        except Exception as exc:
            logger.exception("DB error: %s", exc)

    unlock_msg = ""
    if updated.pads >= 500 and db_user.pads < 500:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>دختر خوب</b> و <b>پسر خوب</b> هم بزنی!"
    elif updated.pads >= 1000 and db_user.pads < 1000:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>نون بربری</b> هم بزنی!"
    elif updated.pads >= 3000 and db_user.pads < 3000:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>آجر</b> هم بزنی!"
    elif updated.pads >= 6000 and db_user.pads < 6000:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>شمع</b> هم بزنی!"
    elif updated.pads >= 10000 and db_user.pads < 10000:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>سیفید</b> هم بزنی!"
    elif updated.pads >= 20000 and db_user.pads < 20000:
        unlock_msg = "\n\n🎉 <b>تبریک!</b> حالا می‌تونی <b>شومپد</b> هم بزنی!"

    await update.message.reply_text(
        f"🎉 <b>{points} {text} پد گرفتی</b>\n\n"
        f"💎 پد هات : <b>{updated.pads}</b>\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری{unlock_msg}{bread_msg}",
        parse_mode=ParseMode.HTML,
    )
