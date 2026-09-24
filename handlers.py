import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import (
    back_keyboard,
    help_back_keyboard,
    help_keyboard,
    shop_keyboard,
    start_keyboard,
)
from messages import (
    HELP_FULL_TEXT,
    HELP_MENU_TEXT,
    HELP_SHORT_TEXT,
    START_TEXT,
)
from repository import (
    RESOURCE_MAP,
    add_pads,
    get_or_create_user,
    get_or_create_user_by_id,
    get_top_users,
    get_user_by_id,
    get_user_by_username,
    give_reward,
    increment_invite_count,
    mark_bread_used,
    seconds_remaining,
    set_user_pads,
    transfer_resource,
    transfer_shields,
    update_resources,
)

logger = logging.getLogger(__name__)


CHANNEL_ID = -1004372622419
CHANNEL_LINK = "https://t.me/SchompedCanal"
BOT_USERNAME = "Schompedbot"

INVITER_REWARD = 500
INVITED_REWARD = 250

# 🎯 سازنده‌های ربات
ADMIN_IDS = [7803165903, 1844792522]

# 🎯 منطقه‌ی زمانی تهران
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


KEYWORDS: dict[str, tuple[int, int]] = {
    "گل رز": (2, 0),
    "دختر خوب": (5, 500),
    "پسر خوب": (5, 500),
    "نون بربری": (5, 1000),
    "آجر": (5, 3000),
    "اجر": (5, 3000),
    "شمع": (5, 6000),
    "سیفید": (5, 10000),
    "شومپد": (10, 20000),
}

KEYWORD_RESOURCE = {
    "گل رز": "pad_rose",
    "دختر خوب": "pad_girl",
    "پسر خوب": "pad_boy",
    "شمع": "pad_candle",
    "آجر": "bricks",
    "اجر": "bricks",
    "نون بربری": "bread_count",
    "سیفید": "shields",
    "شومپد": None,
}

CMD_HELP = "راهنما"
CMD_PROFILE = "پروفایل"
CMD_TOP = "برترها"
CMD_RESOURCES = "منابع"


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


def invite_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "📤 اشتراک‌گذاری لینک",
                url=f"https://t.me/share/url?url={invite_link}&text=بیا توی شومپد بازی کنیم!",
                style="primary",
            )
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="menu_back", style="danger"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def format_user_profile(db_user, remaining: int) -> str:
    now = datetime.now(TEHRAN_TZ)
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M:%S")

    if remaining > 0:
        minutes = remaining // 60
        secs = remaining % 60
        cooldown = f"⏳ {minutes} دقیقه و {secs} ثانیه" if minutes > 0 else f"⏳ {secs} ثانیه"
    else:
        cooldown = "✅ آماده"

    username = f"@{db_user.username}" if db_user.username else "ندارد"
    name = db_user.first_name or "دوست عزیز"

    return (
        f"👤 <b>پروفایل {name}</b>\n\n"
        f"📛 نام: <b>{name}</b>\n"
        f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
        f"🔗 یوزرنیم: <b>{username}</b>\n\n"
        f"💎 <b>منابع:</b>\n"
        f"💎 پدها: <b>{db_user.pads:,}</b>\n"
        f"🥩 گوشت: <b>{db_user.meat:,}</b>\n"
        f"🍵 چای: <b>{db_user.tea:,}</b>\n"
        f"🧱 آجر: <b>{db_user.bricks:,}</b>\n"
        f"🥖 نون بربری: <b>{db_user.bread_count:,}</b>\n"
        f"🍰 کیک یزدی: <b>{db_user.cake:,}</b>\n"
        f"🔪 سیفید: <b>{db_user.shields:,}</b>\n\n"
        f"🌹 گل رز: <b>{db_user.pad_rose:,}</b>\n"
        f"🌸 دختر خوب: <b>{db_user.pad_girl:,}</b>\n"
        f"🌟 پسر خوب: <b>{db_user.pad_boy:,}</b>\n"
        f"🕯️ شمع: <b>{db_user.pad_candle:,}</b>\n\n"
        f"⚔️ <b>جنگجوها:</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
        f"🛡️ لر: <b>{db_user.lords:,}</b>\n\n"
        f"🎁 تعداد دعوت: <b>{db_user.invite_count}</b>\n"
        f"⏳ وضعیت جایزه: {cooldown}\n\n"
        f"📅 تاریخ: <b>{date_str}</b>\n"
        f"🕐 ساعت: <b>{time_str}</b> (تهران)"
    )


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return

    inviter_id: int | None = None
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("invite_"):
            try:
                inviter_id = int(arg.replace("invite_", ""))
            except ValueError:
                inviter_id = None

    if not await is_user_member(context, user.id):
        await update.message.reply_text(
            "🔒 <b>برای استفاده از ربات شومپد، اول باید توی کانال ما عضو بشی!</b>\n\n"
            "📢 روی دکمه زیر بزن و عضو شو، بعد روی «✅ عضو شدم» بزن:",
            parse_mode=ParseMode.HTML,
            reply_markup=join_keyboard(),
        )
        if inviter_id is not None:
            context.user_data["pending_inviter"] = inviter_id
        return

    try:
        db_user, is_new = await get_or_create_user(
            user.id, user.username, user.first_name, invited_by=inviter_id
        )
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        db_user, is_new = None, False

    if is_new and inviter_id is not None and inviter_id != user.id:
        await process_invite(update, context, inviter_id, user)

    pending = context.user_data.pop("pending_inviter", None)
    if pending and is_new and pending != user.id:
        await process_invite(update, context, pending, user)

    await update.message.reply_text(
        START_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


async def process_invite(update, context, inviter_id: int, new_user) -> None:
    if inviter_id == new_user.id:
        return

    try:
        await add_pads(inviter_id, INVITER_REWARD)
        await increment_invite_count(inviter_id)
        await add_pads(new_user.id, INVITED_REWARD)

        if update.message:
            await update.message.reply_text(
                f"🎉 <b>تبریک!</b>\n\n"
                f"💎 <b>{INVITED_REWARD} پد</b> به خاطر دعوت دوستت گرفتی!",
                parse_mode=ParseMode.HTML,
            )

        try:
            await context.bot.send_message(
                chat_id=inviter_id,
                text=(
                    f"🎉 <b>یه نفر با لینک تو اومد!</b>\n\n"
                    f"👤 <b>{new_user.first_name or 'کاربر جدید'}</b>\n"
                    f"💎 <b>{INVITER_REWARD} پد</b> بهت اضافه شد!"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:
            logger.exception("send_message to inviter error: %s", exc)

    except Exception as exc:
        logger.exception("process_invite error: %s", exc)


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

    inviter_id = context.user_data.pop("pending_inviter", None)

    try:
        db_user, is_new = await get_or_create_user(
            user.id, user.username, user.first_name, invited_by=inviter_id
        )
    except Exception as exc:
        logger.exception("DB error: %s", exc)

    if inviter_id is not None and is_new and inviter_id != user.id:
        await process_invite(update, context, inviter_id, user)

    await query.edit_message_text(
        START_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


# ─────────────────────────────────────────────
# دکمه‌های منو
# ─────────────────────────────────────────────
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

    if data == "help_short":
        await query.edit_message_text(
            HELP_SHORT_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_back_keyboard(),
            disable_web_page_preview=True,
        )
        return

    if data == "help_full":
        await query.edit_message_text(
            HELP_FULL_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_back_keyboard(),
            disable_web_page_preview=True,
        )
        return

    if data == "help_back":
        await query.edit_message_text(
            HELP_MENU_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_keyboard(),
            disable_web_page_preview=True,
        )
        return

    # ─── حساب من ───
    if data == "menu_profile":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا در دریافت اطلاعات.", reply_markup=back_keyboard())
            return

        remaining = seconds_remaining(db_user)
        text = format_user_profile(db_user, remaining)

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── فروشگاه ───
    if data == "menu_shop":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا در دریافت اطلاعات.", reply_markup=back_keyboard())
            return

        await query.edit_message_text(
            f"🛒 <b>فروشگاه شومپد</b>\n\n"
            f"💰 موجودی تو:\n"
            f"🥖 نون بربری: <b>{db_user.bread_count:,}</b>\n"
            f"🧱 آجر: <b>{db_user.bricks:,}</b>\n"
            f"🍰 کیک یزدی: <b>{db_user.cake:,}</b>\n\n"
            f"🔪 کارگر افغانی — ۱۰۰ نون بربری\n"
            f"🛡️ لر — ۵۰ آجر\n"
            f"🍰 کیک یزدی — ۱۰ نون بربری",
            parse_mode=ParseMode.HTML,
            reply_markup=shop_keyboard(),
        )
        return

    # ─── خرید کارگر افغانی ───
    if data == "shop_buy_worker":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.answer("❌ خطا", show_alert=True)
            return

        if db_user.bread_count < 100:
            await query.answer(
                f"❌ موجودی کافی نداری!\n\n"
                f"🥖 نیاز: ۱۰۰ نون بربری\n"
                f"💰 موجودی تو: {db_user.bread_count:,}\n\n"
                f"📉 {100 - db_user.bread_count:,} نون بربری دیگه لازم داری.",
                show_alert=True,
            )
            return

        await update_resources(
            user.id,
            bread_count=db_user.bread_count - 100,
            workers=db_user.workers + 1,
        )
        await query.answer("✅ یه کارگر افغانی خریدی!", show_alert=True)
        return

    # ─── خرید لر ───
    if data == "shop_buy_lord":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.answer("❌ خطا", show_alert=True)
            return

        if db_user.bricks < 50:
            await query.answer(
                f"❌ موجودی کافی نداری!\n\n"
                f"🧱 نیاز: ۵۰ آجر\n"
                f"💰 موجودی تو: {db_user.bricks:,}\n\n"
                f"📉 {50 - db_user.bricks:,} آجر دیگه لازم داری.",
                show_alert=True,
            )
            return

        await update_resources(
            user.id,
            bricks=db_user.bricks - 50,
            lords=db_user.lords + 1,
        )
        await query.answer("✅ یه لر خریدی!", show_alert=True)
        return

    # ─── خرید کیک یزدی ───
    if data == "shop_buy_cake":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.answer("❌ خطا", show_alert=True)
            return

        if db_user.bread_count < 10:
            await query.answer(
                f"❌ موجودی کافی نداری!\n\n"
                f"🥖 نیاز: ۱۰ نون بربری\n"
                f"💰 موجودی تو: {db_user.bread_count:,}\n\n"
                f"📉 {10 - db_user.bread_count:,} نون بربری دیگه لازم داری.",
                show_alert=True,
            )
            return

        await update_resources(
            user.id,
            bread_count=db_user.bread_count - 10,
            cake=db_user.cake + 1,
        )
        await query.answer("✅ یه کیک یزدی خریدی!", show_alert=True)
        return

    # ─── برترها ───
    if data == "menu_top":
        try:
            top_users = await get_top_users(10)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا", reply_markup=back_keyboard())
            return

        if not top_users:
            await query.edit_message_text("🏆 هنوز کسی پدی نگرفته!", reply_markup=back_keyboard())
            return

        medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 7
        lines = ["🏆 <b>۱۰ نفر برتر شومپد</b>\n"]
        for i, u in enumerate(top_users):
            name = u.first_name or u.username or f"کاربر {u.telegram_id}"
            lines.append(f"{medals[i]} <b>{name}</b> — {u.pads:,} پد")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── دعوت دوستان ───
    if data == "menu_invite":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا", reply_markup=back_keyboard())
            return

        invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_{user.id}"

        await query.edit_message_text(
            f"🎁 <b>دعوت دوستان</b>\n\n"
            f"با دعوت دوستات، هم تو پد می‌گیری هم اون‌ها!\n\n"
            f"💎 <b>پاداش‌ها:</b>\n"
            f"• تو: <b>{INVITER_REWARD} پد</b> برای هر دعوت موفق\n"
            f"• دوستت: <b>{INVITED_REWARD} پد</b> بعد از عضو شدن\n\n"
            f"👥 تعداد دعوت‌های موفق تو: <b>{db_user.invite_count}</b>\n\n"
            f"🔗 <b>لینک دعوت اختصاصی تو:</b>\n"
            f"<code>{invite_link}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=invite_keyboard(invite_link),
            disable_web_page_preview=True,
        )
        return


# ─────────────────────────────────────────────
# راهنما، پروفایل، برترها، منابع
# ─────────────────────────────────────────────
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        HELP_MENU_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=help_keyboard(),
        disable_web_page_preview=True,
    )


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    remaining = seconds_remaining(db_user)
    text = format_user_profile(db_user, remaining)

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


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
        lines.append(f"{medals[i]} <b>{name}</b> — {u.pads:,} پد")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def resources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if db_user.pads < 6000:
        await update.message.reply_text(
            "🔒 بخش منابع وقتی <b>شمع</b> برات باز بشه فعال می‌شه! (۶۰۰۰ پد)",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text(
        f"🎒 <b>منابع تو</b>\n\n"
        f"🥩 گوشت: <b>{db_user.meat:,}</b>\n"
        f"🍵 چای: <b>{db_user.tea:,}</b>\n"
        f"🧱 آجر: <b>{db_user.bricks:,}</b>\n"
        f"🥖 نون بربری: <b>{db_user.bread_count:,}</b>\n"
        f"🍰 کیک یزدی: <b>{db_user.cake:,}</b>\n"
        f"🔪 سیفید: <b>{db_user.shields:,}</b>\n\n"
        f"🌹 گل رز: <b>{db_user.pad_rose:,}</b>\n"
        f"🌸 دختر خوب: <b>{db_user.pad_girl:,}</b>\n"
        f"🌟 پسر خوب: <b>{db_user.pad_boy:,}</b>\n"
        f"🕯️ شمع: <b>{db_user.pad_candle:,}</b>\n\n"
        f"⚔️ <b>جنگجوها:</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
        f"🛡️ لر: <b>{db_user.lords:,}</b>",
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
# حمله
# ─────────────────────────────────────────────
async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) < 3:
        await update.message.reply_text(
            "❌ فرمت درست:\n"
            "<code>حمله [آی‌دی/یوزرنیم] [تعداد کارگر افغانی]</code>\n\n"
            "مثال: <code>حمله @ali 10</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_str = parts[1]

    try:
        worker_count = int(parts[2])
        if worker_count <= 0:
            raise ValueError    except ValueError:
        await update.message.reply_text("❌ تعداد کارگر باید یه عدد مثبت باشه!")
        return

    try:
        attacker, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if attacker.pads < 6000:
        await update.message.reply_text(
            "🔒 بخش جنگ وقتی <b>شمع</b> برات باز بشه فعال می‌شه! (۶۰۰۰ پد)",
            parse_mode=ParseMode.HTML,
        )
        return

    if attacker.workers < worker_count:
        await update.message.reply_text(
            f"❌ کارگر افغانی کافی نداری!\n"
            f"🔪 موجودی تو: <b>{attacker.workers:,}</b>\n"
            f"🎯 نیاز: <b>{worker_count:,}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_user = None
    if target_str.startswith("@"):
        target_user = await get_user_by_username(target_str)
    else:
        try:
            target_id = int(target_str)
            target_user = await get_user_by_id(target_id)
        except ValueError:
            pass

    if target_user is None:
        await update.message.reply_text("❌ کاربر پیدا نشد!")
        return

    if target_user.telegram_id == user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت حمله کنی!")
        return

    target_name = target_user.first_name or target_user.username or "کاربر"

    available_lords = min(target_user.lords, target_user.bricks)
    workers_killed = available_lords * 4
    remaining_workers = max(0, worker_count - workers_killed)

    if available_lords == 0:
        remaining_workers = worker_count
        attacker_new_workers = attacker.workers
    else:
        attacker_new_workers = attacker.workers - (worker_count - remaining_workers)
        if attacker_new_workers < 0:
            attacker_new_workers = 0

    stolen_tea = remaining_workers * 3
    stolen_meat = remaining_workers * 1

    stolen_tea = min(stolen_tea, target_user.tea)
    stolen_meat = min(stolen_meat, target_user.meat)

    await update_resources(
        user.id,
        workers=attacker_new_workers,
        tea=attacker.tea + stolen_tea,
        meat=attacker.meat + stolen_meat,
    )

    new_lords = target_user.lords - available_lords
    new_bricks = target_user.bricks - available_lords
    new_tea = target_user.tea - stolen_tea
    new_meat = target_user.meat - stolen_meat

    await update_resources(
        target_user.telegram_id,
        lords=new_lords,
        bricks=new_bricks,
        tea=new_tea,
        meat=new_meat,
    )

    result_lines = [f"⚔️ <b>نتیجه‌ی حمله</b>\n"]
    result_lines.append(f"👤 حمله‌کننده: <b>{attacker.first_name}</b>")
    result_lines.append(f"🎯 هدف: <b>{target_name}</b>")
    result_lines.append(f"🔪 کارگرهای فرستاده‌شده: <b>{worker_count:,}</b>")
    result_lines.append("")

    if available_lords > 0:
        result_lines.append(f"🛡️ لرهای دفاعی حریف: <b>{available_lords:,}</b>")
        result_lines.append(f"💀 کارگرهای کشته‌شده: <b>{worker_count - remaining_workers:,}</b>")
        result_lines.append(f"🧱 آجر مصرف‌شده: <b>{available_lords:,}</b>")

    result_lines.append(f"🔪 کارگرهای باقی‌مونده: <b>{remaining_workers:,}</b>")
    result_lines.append("")

    if remaining_workers > 0:
        result_lines.append(f"🎁 <b>دزدی:</b>")
        result_lines.append(f"🥩 گوشت: <b>+{stolen_meat:,}</b>")
        result_lines.append(f"🍵 چای: <b>+{stolen_tea:,}</b>")
    else:
        result_lines.append(f"💥 <b>حمله شکست خورد!</b>")

    await update.message.reply_text(
        "\n".join(result_lines),
        parse_mode=ParseMode.HTML,
    )


async def transfer_shield_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    parts = text.split()
    if len(parts) < 4:
        await update.message.reply_text(
            "❌ فرمت درست:\n<code>پرت سیفید [آی‌دی عددی/یوزرنیم] [تعداد]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_str = parts[2]
    try:
        amount = int(parts[3])
    except ValueError:
        await update.message.reply_text("❌ تعداد باید عدد باشه!")
        return

    try:
        sender, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if sender.shields < amount:
        await update.message.reply_text(
            f"❌ سیفید کافی نداری!\nموجودی: <b>{sender.shields:,}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_user = None
    if target_str.startswith("@"):
        target_user = await get_user_by_username(target_str)
    else:
        try:
            target_id = int(target_str)
            target_user = await get_user_by_id(target_id)
        except ValueError:
            pass

    if target_user is None:
        await update.message.reply_text("❌ کاربر پیدا نشد!")
        return

    if target_user.telegram_id == user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت سیفید پرت کنی!")
        return

    success = await transfer_shields(user.id, target_user.telegram_id, amount)

    if success:
        target_name = target_user.first_name or target_user.username or "کاربر"
        await update.message.reply_text(
            f"🎁 <b>{amount:,} سیفید</b> به <b>{target_name}</b> پرت کردی!",
            parse_mode=ParseMode.HTML,
        )


# ─────────────────────────────────────────────
# ابزار انتقال
# ─────────────────────────────────────────────
def extract_target_from_message(message, parts_offset: int) -> tuple[int | None, str | None]:
    """کاربر هدف رو از پیام پیدا می‌کنه."""
    # ─── حالت ۱: ریپلای ───
    if message.reply_to_message is not None:
        replied = message.reply_to_message

        # ۱.۱: ریپلای روی پیام کاربر
        if replied.from_user is not None and not replied.from_user.is_bot:
            return replied.from_user.id, None

        # ۱.۲: ریپلای روی پیامی که متنش آی‌دی عددیه
        if replied.text:
            replied_text = replied.text.strip()
            if replied_text.isdigit():
                return int(replied_text), None

    # ─── حالت ۲: آی‌دی/یوزرنیم توی خود دستور ───
    parts = message.text.split()
    if len(parts) > parts_offset:
        target_str = parts[parts_offset]
        if target_str.startswith("@"):
            return None, target_str
        elif target_str.lstrip("-").isdigit():
            return int(target_str), None

    return None, None


async def resolve_target(target_id: int | None, target_username: str | None):
    """کاربر رو از آی‌دی یا یوزرنیم پیدا می‌کنه.
    
    - اگه با آی‌دی عددی: کاربر اگه نباشه، ساخته می‌شه
    - اگه با یوزرنیم: باید قبلاً ربات رو استارت کرده باشه
    """
    if target_id is not None:
        user, _ = await get_or_create_user_by_id(target_id)
        return user
    if target_username is not None:
        return await get_user_by_username(target_username)
    return None


# ─────────────────────────────────────────────
# انتقال منابع توسط سازنده‌ها (بی‌نهایت)
# ─────────────────────────────────────────────
async def admin_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتقال هر منبعی توسط سازنده‌ها — بی‌نهایت."""
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    if user.id not in ADMIN_IDS:
        return

    parts = text.split()

    if len(parts) < 3:
        await update.message.reply_text(
            "❌ فرمت درست:\n"
            "<code>انتقال [منبع] [تعداد] [آی‌دی/یوزرنیم]</code>\n"
            "یا\n"
            "<code>انتقال [منبع] [تعداد]</code> + ریپلای\n\n"
            "📋 منابع قابل انتقال:\n"
            "پد، گوشت، چای، آجر، نون بربری، کیک یزدی، سیفید،\n"
            "کارگر افغانی، لر، گل رز، دختر خوب، پسر خوب، شمع",
            parse_mode=ParseMode.HTML,
        )
        return

    resource_name = parts[1]
    if resource_name not in RESOURCE_MAP:
        await update.message.reply_text(
            f"❌ منبع <b>{resource_name}</b> شناخته نشد!\n\n"
            f"📋 منابع معتبر:\n"
            f"<code>پد، گوشت، چای، آجر، نون بربری، کیک یزدی، سیفید،\n"
            f"کارگر افغانی، لر، گل رز، دختر خوب، پسر خوب، شمع</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        amount = int(parts[2])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ تعداد باید یه عدد مثبت باشه!")
        return

    target_id, target_username = extract_target_from_message(update.message, 3)
    target_user = await resolve_target(target_id, target_username)

    if target_user is None:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد!\n\n"
            "📋 روش‌های درست:\n"
            "1️⃣ <code>انتقال پد 1000 1844792522</code>\n"
            "2️⃣ <code>انتقال پد 1000 @ali</code>\n"
            "3️⃣ <code>انتقال پد 1000</code> + ریپلای روی پیام کاربر\n"
            "4️⃣ <code>انتقال پد 1000</code> + ریپلای روی پیامی که آی‌دی عددی نوشته",
            parse_mode=ParseMode.HTML,
        )
        return

    column = RESOURCE_MAP[resource_name]
    receiver_current = getattr(target_user, column)
    receiver_new = receiver_current + amount

    await update_resources(target_user.telegram_id, **{column: receiver_new})

    target_name = target_user.first_name or target_user.username or "کاربر"

    await update.message.reply_text(
        f"✅ <b>{amount:,} {resource_name}</b> به <b>{target_name}</b> منتقل شد!\n\n"
        f"📦 موجودی جدید گیرنده: <b>{receiver_new:,}</b>\n"
        f"♾️ موجودی تو: <b>بی‌نهایت</b> (دست‌نخورده)",
        parse_mode=ParseMode.HTML,
    )

    try:
        await context.bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                f"🎁 <b>یه هدیه از طرف مدیریت!</b>\n\n"
                f"📦 <b>{amount:,} {resource_name}</b> بهت داده شد.\n"
                f"💰 موجودی جدید تو: <b>{receiver_new:,}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("send_message to receiver error: %s", exc)


async def admin_remove_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف انتقال هر منبعی توسط سازنده‌ها — بی‌نهایت."""
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    if user.id not in ADMIN_IDS:
        return

    parts = text.split()

    if len(parts) < 4:
        await update.message.reply_text(
            "❌ فرمت درست:\n"
            "<code>حذف انتقال [منبع] [تعداد] [آی‌دی/یوزرنیم]</code>\n"
            "یا\n"
            "<code>حذف انتقال [منبع] [تعداد]</code> + ریپلای",
            parse_mode=ParseMode.HTML,
        )
        return

    resource_name = parts[2]
    if resource_name not in RESOURCE_MAP:
        await update.message.reply_text(
            f"❌ منبع <b>{resource_name}</b> شناخته نشد!",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        amount = int(parts[3])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ تعداد باید یه عدد مثبت باشه!")
        return

    target_id, target_username = extract_target_from_message(update.message, 4)
    target_user = await resolve_target(target_id, target_username)

    if target_user is None:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد!\n\n"
            "📋 روش‌های درست:\n"
            "1️⃣ <code>حذف انتقال پد 500 1844792522</code>\n"
            "2️⃣ <code>حذف انتقال پد 500 @ali</code>\n"
            "3️⃣ <code>حذف انتقال پد 500</code> + ریپلای روی پیام کاربر",
            parse_mode=ParseMode.HTML,
        )
        return

    column = RESOURCE_MAP[resource_name]
    receiver_current = getattr(target_user, column)
    receiver_new = receiver_current - amount

    await update_resources(target_user.telegram_id, **{column: receiver_new})

    target_name = target_user.first_name or target_user.username or "کاربر"

    await update.message.reply_text(
        f"✅ <b>{amount:,} {resource_name}</b> از <b>{target_name}</b> پس گرفته شد!\n\n"
        f"📦 موجودی جدید گیرنده: <b>{receiver_new:,}</b>\n"
        f"♾️ موجودی تو: <b>بی‌نهایت</b> (دست‌نخورده)",
        parse_mode=ParseMode.HTML,
    )

    try:
        await context.bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                f"⚠️ <b>اطلاعیه مدیریت</b>\n\n"
                f"📦 <b>{amount:,} {resource_name}</b> ازت پس گرفته شد.\n"
                f"💰 موجودی جدید تو: <b>{receiver_new:,}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("send_message to receiver error: %s", exc)


# ─────────────────────────────────────────────
# خروج از گروه (فقط سازنده‌ها)
# ─────────────────────────────────────────────
async def leave_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور خروج — ربات از گروه لفت می‌ده.
    
    فقط سازنده‌ها می‌تونن از این دستور استفاده کنن.
    """
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    chat = update.effective_chat

    if user.id not in ADMIN_IDS:
        return

    if chat is None or chat.type not in ("group", "supergroup"):
        return

    try:
        await update.message.reply_text(
            "👋 <b>خداحافظ!</b>\n\n"
            "از طرف سازنده‌ها، ربات داره از این گروه می‌ره.\n"
            "اگه دوباره خواستی، ربات رو به گروه اضافه کن. 🌹",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Send goodbye error: %s", exc)

    try:
        await context.bot.leave_chat(chat_id=chat.id)
        logger.info(f"Left group {chat.id} ({chat.title}) by admin {user.id}")
    except Exception as exc:
        logger.exception("leave_chat error: %s", exc)


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
    if text == CMD_RESOURCES:
        await resources_handler(update, context)
        return
    if text.startswith("پرت سیفید"):
        await transfer_shield_handler(update, context)
        return

    # 🆕 خروج از گروه (فقط سازنده‌ها)
    if text == "خروج":
        if user.id not in ADMIN_IDS:
            return
        await leave_group_handler(update, context)
        return

    # حمله
    if text.startswith("حمله "):
        await attack_handler(update, context)
        return

    # حذف انتقال
    if text.startswith("حذف انتقال"):
        if user.id not in ADMIN_IDS:
            return
        await admin_remove_transfer_handler(update, context)
        return

    # انتقال
    if text.startswith("انتقال"):
        if user.id not in ADMIN_IDS:
            return
        await admin_transfer_handler(update, context)
        return

    # کلمات کلیدی
    if text not in KEYWORDS:
        return

    points, required_pads = KEYWORDS[text]

    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
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
            f"💎 پدهای فعلی: <b>{db_user.pads:,}</b>\n"
            f"🎯 نیاز: <b>{required_pads:,}</b> پد\n"
            f"📉 <b>{needed:,} پد</b> دیگه لازم داری.",
            parse_mode=ParseMode.HTML,
        )
        return

    remaining = seconds_remaining(db_user)
    if remaining > 0:
        minutes = remaining // 60
        secs = remaining % 60
        wait_text = f"{minutes} دقیقه و {secs} ثانیه" if minutes > 0 else f"{secs} ثانیه"

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

    resource_column = KEYWORD_RESOURCE.get(text)
    if resource_column is not None:
        current_val = getattr(updated, resource_column)
        await update_resources(user.id, **{resource_column: current_val + points})

    bread_msg = ""
    if text == "نون بربری":
        await mark_bread_used(user.id)
        bread_msg = "\n\n⚠️ از این به بعد <b>دختر خوب</b> و <b>پسر خوب</b> برات قفل شده!"

    fresh_user, _ = await get_or_create_user(user.id, user.username, user.first_name)

    resource_lines = []
    if text == "گل رز":
        resource_lines.append(f"🌹 گل رز های تو: <b>{fresh_user.pad_rose:,}</b>")
    elif text == "دختر خوب":
        resource_lines.append(f"🌸 دختر خوب های تو: <b>{fresh_user.pad_girl:,}</b>")
    elif text == "پسر خوب":
        resource_lines.append(f"🌟 پسر خوب های تو: <b>{fresh_user.pad_boy:,}</b>")
    elif text == "شمع":
        resource_lines.append(f"🕯️ شمع های تو: <b>{fresh_user.pad_candle:,}</b>")
    elif text in ("آجر", "اجر"):
        resource_lines.append(f"🧱 آجر های تو: <b>{fresh_user.bricks:,}</b>")
    elif text == "نون بربری":
        resource_lines.append(f"🥖 نون بربری های تو: <b>{fresh_user.bread_count:,}</b>")
    elif text == "سیفید":
        resource_lines.append(f"🔪 سیفید های تو: <b>{fresh_user.shields:,}</b>")

    resource_text = "\n".join(resource_lines)
    resource_text = f"\n{resource_text}\n" if resource_text else ""

    await update.message.reply_text(
        f"🎉 <b>{points} {text} پد گرفتی</b>\n"
        f"{resource_text}"
        f"💎 پد هات : <b>{fresh_user.pads:,}</b>\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری{bread_msg}",
        parse_mode=ParseMode.HTML,
    )
