import asyncio
import logging
import random
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
    HUNGRY_DAYS_LIMIT,
    RESOURCE_MAP,
    add_or_update_group,
    add_pads,
    get_active_groups_count,
    get_all_groups,
    get_or_create_user,
    get_or_create_user_by_id,
    get_stats,
    get_top_users,
    get_user_by_id,
    get_user_by_username,
    give_reward,
    increment_invite_count,
    log_report,
    mark_bread_used,
    mark_group_removed,
    process_daily_food,
    seconds_remaining,
    set_user_pads,
    transfer_shields,
    update_resources,
)

logger = logging.getLogger(__name__)


CHANNEL_ID = -1004372622419
CHANNEL_LINK = "https://t.me/SchompedCanal"
BOT_USERNAME = "Schompedbot"

INVITER_REWARD = 500
INVITED_REWARD = 250

ADMIN_IDS = [7803165903, 1844792522]

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

HELP_TIMEOUT_SECONDS = 300  # ۵ دقیقه


KEYWORDS: dict[str, tuple[int, int]] = {
    "گل رز": (2, 0),
    "دختر خوب": (5, 500),
    "پسر خوب": (5, 500),
    "نون بربری": (5, 1000),
    "آجر": (5, 3000),
    "اجر": (5, 3000),
    "سیفید": (5, 10000),
    "شومپد": (10, 20000),
}

KEYWORD_RESOURCE = {
    "گل رز": "pad_rose",
    "دختر خوب": "pad_girl",
    "پسر خوب": "pad_boy",
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
CMD_REPORT = "گزارش"
CMD_SHOP = "فروشگاه"


# ═════════════════════════════════════════════
# ابزار عمومی
# ═════════════════════════════════════════════
async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = member.status
        return status in ("member", "administrator", "creator")
    except Exception as exc:
        logger.exception("get_chat_member error: %s", exc)
        return True


async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.exception(f"send to admin {admin_id} error: %s", exc)


def join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK, style="primary")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership", style="success")],
    ])


def invite_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📤 اشتراک‌گذاری لینک",
            url=f"https://t.me/share/url?url={invite_link}&text=بیا توی شومپد بازی کنیم!",
            style="primary",
        )],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_back", style="danger")],
    ])


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

    hungry_status = ""
    if db_user.hungry_days > 0:
        remaining_days = HUNGRY_DAYS_LIMIT - db_user.hungry_days
        hungry_status = (
            f"\n⚠️ <b>گرسنگی:</b> {db_user.hungry_days}/{HUNGRY_DAYS_LIMIT} روز\n"
            f"💀 {remaining_days} روز دیگه تا مرگ جنگجوها!\n"
        )

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
        f"🌟 پسر خوب: <b>{db_user.pad_boy:,}</b>\n\n"
        f"⚔️ <b>جنگجوها:</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
        f"🛡️ لر: <b>{db_user.lords:,}</b>\n"
        f"{hungry_status}\n"
        f"🎁 تعداد دعوت: <b>{db_user.invite_count}</b>\n"
        f"⏳ وضعیت جایزه: {cooldown}\n\n"
        f"📅 تاریخ: <b>{date_str}</b>\n"
        f"🕐 ساعت: <b>{time_str}</b> (تهران)"
    )


async def check_daily_food(telegram_id: int, update: Update) -> None:
    try:
        result = await process_daily_food(telegram_id)
    except Exception as exc:
        logger.exception("process_daily_food error: %s", exc)
        return

    if not result["processed"]:
        return

    if update.message is None:
        return

    if result["starved"]:
        await update.message.reply_text(
            f"💀 <b>جنگجوهای تو از گرسنگی مردن!</b>\n\n"
            f"📅 {HUNGRY_DAYS_LIMIT} روز گرسنه موندن و نتونستن خوراکشون رو بدن.\n\n"
            f"🔪 کارگرهای افغانی از دست رفته: <b>{result['workers_lost']:,}</b>\n"
            f"🛡️ لرهای از دست رفته: <b>{result['lords_lost']:,}</b>",
            parse_mode=ParseMode.HTML,
        )
    elif result["days"] > 1:
        await update.message.reply_text(
            f"🍽️ <b>مصرف روزانه</b>\n\n"
            f"📅 {result['days']} روز گذشته.\n"
            f"🥩 گوشت مصرف‌شده: <b>{result['meat_needed']:,}</b>\n"
            f"🍰 کیک یزدی مصرف‌شده: <b>{result['cake_needed']:,}</b>",
            parse_mode=ParseMode.HTML,
        )


# ═════════════════════════════════════════════
# بستن خودکار پنل راهنما
# ═════════════════════════════════════════════
async def auto_close_help_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    owner_id: int,
    delay: int = HELP_TIMEOUT_SECONDS,
) -> None:
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    try:
        current_panel = context.user_data.get("help_panel_msg_id")
        if current_panel == message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            context.user_data.pop("help_panel_msg_id", None)
            context.user_data.pop("help_panel_chat_id", None)
            logger.info(f"Auto-closed help panel for user {owner_id}")
    except Exception as exc:
        logger.exception("auto_close error: %s", exc)


# ═════════════════════════════════════════════
# گزارش گروه
# ═════════════════════════════════════════════
async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    chat = message.chat
    if chat.type not in ("group", "supergroup"):
        return

    added_by = None
    added_by_name = "نامعلوم"
    if message.from_user is not None:
        added_by = message.from_user.id
        added_by_name = message.from_user.first_name or "کاربر"

    try:
        member_count = await context.bot.get_chat_member_count(chat.id)
    except Exception:
        member_count = 0

    try:
        await add_or_update_group(
            group_id=chat.id,
            title=chat.title or "بدون نام",
            added_by=added_by,
            added_by_name=added_by_name,
            member_count=member_count,
        )
        await log_report(
            event_type="new_group",
            description=f"ربات به گروه {chat.title} اضافه شد",
            user_id=added_by,
            group_id=chat.id,
        )
    except Exception as exc:
        logger.exception("add_or_update_group error: %s", exc)

    await notify_admins(
        context,
        f"✅ <b>ربات به گروه جدید اضافه شد!</b>\n\n"
        f"📛 نام گروه: <b>{chat.title or 'بدون نام'}</b>\n"
        f"🆔 آی‌دی گروه: <code>{chat.id}</code>\n"
        f"👤 اضافه‌کننده: <b>{added_by_name}</b> (<code>{added_by or 'نامعلوم'}</code>)\n"
        f"📊 تعداد اعضا: <b>{member_count:,}</b>",
    )


async def bot_left_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    chat = message.chat
    if chat.type not in ("group", "supergroup"):
        return

    removed_by = None
    removed_by_name = "نامعلوم"
    if message.from_user is not None:
        removed_by = message.from_user.id
        removed_by_name = message.from_user.first_name or "کاربر"

    try:
        await mark_group_removed(chat.id)
        await log_report(
            event_type="left_group",
            description=f"ربات از گروه {chat.title} حذف شد",
            user_id=removed_by,
            group_id=chat.id,
        )
    except Exception as exc:
        logger.exception("mark_group_removed error: %s", exc)

    await notify_admins(
        context,
        f"❌ <b>ربات از گروه حذف شد!</b>\n\n"
        f"📛 نام گروه: <b>{chat.title or 'بدون نام'}</b>\n"
        f"🆔 آی‌دی گروه: <code>{chat.id}</code>\n"
        f"👤 حذف‌کننده: <b>{removed_by_name}</b>",
    )


# ═════════════════════════════════════════════
# نمایش فروشگاه
# ═════════════════════════════════════════════
async def shop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش فروشگاه توی گروه."""
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user

    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        await check_daily_food(user.id, update)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    await update.message.reply_text(
        f"🛒 <b>فروشگاه شومپد</b>\n\n"
        f"💰 <b>موجودی تو:</b>\n"
        f"🥖 نون بربری: <b>{db_user.bread_count:,}</b>\n"
        f"🧱 آجر: <b>{db_user.bricks:,}</b>\n"
        f"🍰 کیک یزدی: <b>{db_user.cake:,}</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
        f"🛡️ لر: <b>{db_user.lords:,}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏪 <b>لیست فروش:</b>\n\n"
        f"🔪 <b>کارگر افغانی</b> — ۱۰۰ نون بربری\n"
        f"🛡️ <b>لر</b> — ۵۰ آجر\n"
        f"🍰 <b>کیک یزدی</b> — ۱۰ نون بربری\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 روی دکمه‌ی مورد نظر بزن:",
        parse_mode=ParseMode.HTML,
        reply_markup=shop_keyboard(owner_id=user.id),
    )


# ═════════════════════════════════════════════
# خرید
# ═════════════════════════════════════════════
async def process_buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    buying = context.user_data.get("buying")
    if buying is None:
        return

    if amount < 1 or amount > 1000:
        await update.message.reply_text(
            "❌ عدد باید بین <b>۱</b> تا <b>۱۰۰۰</b> باشه!\n\nدوباره بفرست:",
            parse_mode=ParseMode.HTML,
        )
        return

    item = buying["item"]
    price_per = buying["price_per"]
    price_resource = buying["price_resource"]
    price_name = buying["price_name"]
    total_price = amount * price_per

    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    user_balance = getattr(db_user, price_resource)

    if user_balance < total_price:
        context.user_data.pop("buying", None)
        await update.message.reply_text(
            f"❌ <b>موجودی کافی نداری!</b>\n\n"
            f"🛒 تعداد درخواستی: <b>{amount:,}</b>\n"
            f"💰 هزینه کل: <b>{total_price:,} {price_name}</b>\n"
            f"💼 موجودی تو: <b>{user_balance:,} {price_name}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    buying["amount"] = amount
    buying["total_price"] = total_price
    context.user_data["buying"] = buying

    keyboard = [[
        InlineKeyboardButton("✅ مطمئنم، بخر", callback_data="confirm_buy", style="success"),
        InlineKeyboardButton("❌ لغو", callback_data="cancel_buy", style="danger"),
    ]]

    item_names = {
        "worker": "کارگر افغانی 🔪",
        "lord": "لر 🛡️",
        "cake": "کیک یزدی 🍰",
    }

    await update.message.reply_text(
        f"🛒 <b>تایید خرید</b>\n\n"
        f"📦 آیتم: <b>{item_names.get(item, item)}</b>\n"
        f"🔢 تعداد: <b>{amount:,}</b>\n"
        f"💰 هزینه کل: <b>{total_price:,} {price_name}</b>\n\n"
        f"آیا از خرید مطمئنی؟",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ═════════════════════════════════════════════
# /start
# ═════════════════════════════════════════════
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

    if is_new:
        try:
            await log_report(
                event_type="new_user",
                description=f"کاربر جدید: {user.first_name} (@{user.username})",
                user_id=user.id,
            )
            await notify_admins(
                context,
                f"👤 <b>کاربر جدید!</b>\n\n"
                f"📛 نام: <b>{user.first_name or 'کاربر'}</b>\n"
                f"🆔 آی‌دی: <code>{user.id}</code>\n"
                f"🔗 یوزرنیم: <b>@{user.username or 'ندارد'}</b>\n"
                f"🎁 دعوت‌کننده: <code>{inviter_id or 'ندارد'}</code>",
            )
        except Exception as exc:
            logger.exception("log new user error: %s", exc)

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


# ═════════════════════════════════════════════
# عضویت اجباری
# ═════════════════════════════════════════════
async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


# ═════════════════════════════════════════════
# گزارش آمار
# ═════════════════════════════════════════════
async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    try:
        stats = await get_stats()
        groups = await get_all_groups()
    except Exception as exc:
        logger.exception("stats error: %s", exc)
        await update.message.reply_text("❌ خطا در دریافت آمار")
        return

    lines = [
        f"📊 <b>آمار کلی ربات شومپد</b>\n",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👥 <b>کاربران:</b>",
        f"• کل: <b>{stats['total_users']:,}</b>",
        f"• ۲۴ ساعت اخیر: <b>{stats['users_24h']:,}</b>",
        f"• ۷ روز اخیر: <b>{stats['users_7d']:,}</b>\n",
        f"💬 <b>گروه‌ها:</b>",
        f"• کل: <b>{stats['total_groups']:,}</b>",
        f"• فعال: <b>{stats['active_groups']:,}</b>\n",
        f"⚔️ <b>جنگ‌ها:</b>",
        f"• کل: <b>{stats['total_attacks']:,}</b>",
        f"• ۲۴ ساعت اخیر: <b>{stats['attacks_24h']:,}</b>\n",
        f"🎁 <b>دعوت‌ها:</b> <b>{stats['total_invites']:,}</b>\n",
        f"💰 <b>منابع در گردش:</b>",
        f"• پد: <b>{stats['total_pads']:,}</b>",
        f"• کارگر افغانی: <b>{stats['total_workers']:,}</b>",
        f"• لر: <b>{stats['total_lords']:,}</b>\n",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📋 <b>آخرین ۱۰ گروه:</b>",
    ]

    for g in groups[:10]:
        status = "✅" if g.is_active else "❌"
        lines.append(
            f"{status} <b>{g.title or 'بدون نام'}</b> — "
            f"<code>{g.group_id}</code> — {g.member_count:,} عضو"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ═════════════════════════════════════════════
# دکمه‌های منو
# ═════════════════════════════════════════════
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    user = query.from_user
    if user is None:
        return

    data = query.data

    # ─── بازگشت ───
    if data == "menu_back":
        await query.edit_message_text(
            START_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(),
            disable_web_page_preview=True,
        )
        return

    # ─── بستن عمومی ───
    if data == "menu_close":
        try:
            await query.message.delete()
        except Exception as exc:
            logger.exception("Delete error: %s", exc)
        return

    # ─── راهنما: توضیحات کوتاه ───
    if data.startswith("help_short_"):
        try:
            owner_id = int(data.replace("help_short_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.\n"
                "خودت یه پنل جدید بساز: راهنما",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            HELP_SHORT_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_back_keyboard(owner_id),
            disable_web_page_preview=True,
        )
        return

    # ─── راهنما: توضیحات کامل ───
    if data.startswith("help_full_"):
        try:
            owner_id = int(data.replace("help_full_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.\n"
                "خودت یه پنل جدید بساز: راهنما",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            HELP_FULL_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_back_keyboard(owner_id),
            disable_web_page_preview=True,
        )
        return

    # ─── راهنما: بازگشت ───
    if data.startswith("help_back_"):
        try:
            owner_id = int(data.replace("help_back_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            HELP_MENU_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=help_keyboard(owner_id),
            disable_web_page_preview=True,
        )
        return

    # ─── بستن قفل‌شده ───
    if data.startswith("menu_close_"):
        try:
            owner_id = int(data.replace("menu_close_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.",
                show_alert=True,
            )
            return

        task = context.user_data.pop("help_timeout_task", None)
        if task is not None:
            try:
                task.cancel()
            except Exception:
                pass

        try:
            await query.message.delete()
        except Exception as exc:
            logger.exception("Delete error: %s", exc)

        context.user_data.pop("help_panel_msg_id", None)
        context.user_data.pop("help_panel_chat_id", None)
        return

    # ─── حساب من ───
    if data == "menu_profile":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
            await check_daily_food(user.id, update)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا", reply_markup=back_keyboard())
            return

        remaining = seconds_remaining(db_user)
        text = format_user_profile(db_user, remaining)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())
        return

    # ─── فروشگاه ───
    if data == "menu_shop":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
            await check_daily_food(user.id, update)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا", reply_markup=back_keyboard())
            return

        await query.edit_message_text(
            f"🛒 <b>فروشگاه شومپد</b>\n\n"
            f"💰 <b>موجودی تو:</b>\n"
            f"🥖 نون بربری: <b>{db_user.bread_count:,}</b>\n"
            f"🧱 آجر: <b>{db_user.bricks:,}</b>\n"
            f"🍰 کیک یزدی: <b>{db_user.cake:,}</b>\n"
            f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
            f"🛡️ لر: <b>{db_user.lords:,}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏪 <b>لیست فروش:</b>\n\n"
            f"🔪 <b>کارگر افغانی</b> — ۱۰۰ نون بربری\n"
            f"🛡️ <b>لر</b> — ۵۰ آجر\n"
            f"🍰 <b>کیک یزدی</b> — ۱۰ نون بربری\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.HTML,
            reply_markup=shop_keyboard(owner_id=user.id),
        )
        return

    # ─── خرید کارگر افغانی ───
    if data.startswith("shop_buy_worker_"):
        try:
            owner_id = int(data.replace("shop_buy_worker_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.\n"
                "خودت یه فروشگاه بساز: فروشگاه",
                show_alert=True,
            )
            return

        context.user_data["buying"] = {
            "item": "worker",
            "price_per": 100,
            "price_resource": "bread_count",
            "price_name": "🥖 نون بربری",
        }
        await query.edit_message_text(
            "🔪 <b>خرید کارگر افغانی</b>\n\n"
            "💰 هزینه هر کارگر: <b>۱۰۰ نون بربری</b>\n\n"
            "📝 چند تا کارگر افغانی می‌خوای بخری؟\n"
            "یه عدد بین ۱ تا ۱۰۰۰ بفرست:",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── خرید لر ───
    if data.startswith("shop_buy_lord_"):
        try:
            owner_id = int(data.replace("shop_buy_lord_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.\n"
                "خودت یه فروشگاه بساز: فروشگاه",
                show_alert=True,
            )
            return

        context.user_data["buying"] = {
            "item": "lord",
            "price_per": 50,
            "price_resource": "bricks",
            "price_name": "🧱 آجر",
        }
        await query.edit_message_text(
            "🛡️ <b>خرید لر</b>\n\n"
            "💰 هزینه هر لر: <b>۵۰ آجر</b>\n\n"
            "📝 چند تا لر می‌خوای بخری؟\n"
            "یه عدد بین ۱ تا ۱۰۰۰ بفرست:",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── خرید کیک یزدی ───
    if data.startswith("shop_buy_cake_"):
        try:
            owner_id = int(data.replace("shop_buy_cake_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        if user.id != owner_id:
            await query.answer(
                "⛔ تو دسترسی نداری!\n\n"
                "این پنل مال یه کاربر دیگه‌ست.\n"
                "خودت یه فروشگاه بساز: فروشگاه",
                show_alert=True,
            )
            return

        context.user_data["buying"] = {
            "item": "cake",
            "price_per": 10,
            "price_resource": "bread_count",
            "price_name": "🥖 نون بربری",
        }
        await query.edit_message_text(
            "🍰 <b>خرید کیک یزدی</b>\n\n"
            "💰 هزینه هر کیک: <b>۱۰ نون بربری</b>\n\n"
            "📝 چند تا کیک یزدی می‌خوای بخری؟\n"
            "یه عدد بین ۱ تا ۱۰۰۰ بفرست:",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    # ─── تایید خرید ───
    if data == "confirm_buy":
        buying = context.user_data.get("buying")
        if buying is None or "amount" not in buying:
            await query.answer("❌ خطا در خرید", show_alert=True)
            return

        item = buying["item"]
        amount = buying["amount"]
        total_price = buying["total_price"]
        price_resource = buying["price_resource"]

        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.answer("❌ خطا", show_alert=True)
            return

        user_balance = getattr(db_user, price_resource)
        if user_balance < total_price:
            context.user_data.pop("buying", None)
            await query.edit_message_text(
                f"❌ <b>موجودی کافی نداری!</b>",
                parse_mode=ParseMode.HTML,
            )
            return

        if item == "worker":
            await update_resources(
                user.id,
                bread_count=db_user.bread_count - total_price,
                workers=db_user.workers + amount,
            )
            msg = (
                f"✅ <b>{amount:,} کارگر افغانی</b> خریدی!\n\n"
                f"💰 <b>{total_price:,} نون بربری</b> کم شد.\n"
                f"🔪 موجودی جدید: <b>{db_user.workers + amount:,}</b>"
            )
        elif item == "lord":
            await update_resources(
                user.id,
                bricks=db_user.bricks - total_price,
                lords=db_user.lords + amount,
            )
            msg = (
                f"✅ <b>{amount:,} لر</b> خریدی!\n\n"
                f"💰 <b>{total_price:,} آجر</b> کم شد.\n"
                f"🛡️ موجودی جدید: <b>{db_user.lords + amount:,}</b>"
            )
        elif item == "cake":
            await update_resources(
                user.id,
                bread_count=db_user.bread_count - total_price,
                cake=db_user.cake + amount,
            )
            msg = (
                f"✅ <b>{amount:,} کیک یزدی</b> خریدی!\n\n"
                f"💰 <b>{total_price:,} نون بربری</b> کم شد.\n"
                f"🍰 موجودی جدید: <b>{db_user.cake + amount:,}</b>"
            )
        else:
            msg = "❌ خطا"

        context.user_data.pop("buying", None)
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())
        return

    # ─── لغو خرید ───
    if data == "cancel_buy":
        context.user_data.pop("buying", None)
        await query.edit_message_text("❌ خرید لغو شد.", reply_markup=back_keyboard())
        return

    # ─── حمله ───
    if data.startswith("war_request_"):
        try:
            target_id = int(data.replace("war_request_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        try:
            attacker, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.answer("❌ خطا", show_alert=True)
            return

        if attacker.workers < 1:
            await query.answer("❌ کارگر افغانی نداری! از فروشگاه بخر.", show_alert=True)
            return

        target_user = await get_user_by_id(target_id)
        if target_user is None:
            await query.answer("❌ حریف پیدا نشد!", show_alert=True)
            return

        if target_user.meat <= 0 or target_user.tea <= 0:
            await query.answer(
                f"❌ این کاربر گوشت و چای نداره!\n"
                f"🥩 گوشت: {target_user.meat:,}\n"
                f"🍵 چای: {target_user.tea:,}",
                show_alert=True,
            )
            return

        target_name = target_user.first_name or target_user.username or "کاربر"

        context.user_data["war"] = {
            "attacker_id": user.id,
            "target_id": target_id,
        }

        keyboard = [[
            InlineKeyboardButton("⚔️ تایید جنگ نهایی", callback_data="war_confirm", style="danger"),
            InlineKeyboardButton("❌ انصراف", callback_data="war_cancel", style="success"),
        ]]

        await query.edit_message_text(
            f"📢 <b>درخواست حمله!</b>\n\n"
            f"⚔️ حمله‌کننده: <b>{attacker.first_name}</b>\n"
            f"🎯 هدف: <b>{target_name}</b>\n\n"
            f"🔪 کارگرهای افغانی حمله‌کننده: <b>{attacker.workers:,}</b>\n"
            f"🛡️ لرهای هدف: <b>{target_user.lords:,}</b>\n"
            f"🧱 آجرهای هدف: <b>{target_user.bricks:,}</b>\n\n"
            f"⚠️ آیا از حمله مطمئنی؟",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data == "war_cancel":
        context.user_data.pop("war", None)
        await query.edit_message_text("❌ حمله لغو شد.", reply_markup=back_keyboard())
        return

    if data == "war_confirm":
        war = context.user_data.get("war")
        if war is None:
            await query.answer("❌ خطا در جنگ", show_alert=True)
            return

        if user.id != war["attacker_id"]:
            await query.answer("❌ فقط حمله‌کننده می‌تونه تایید کنه!", show_alert=True)
            return

        context.user_data.pop("war", None)
        await execute_war(update, context, war)
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

        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=back_keyboard())
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


# ═════════════════════════════════════════════
# اجرای جنگ داستانی
# ═════════════════════════════════════════════
async def execute_war(update, context, war: dict) -> None:
    query = update.callback_query

    attacker_id = war["attacker_id"]
    target_id = war["target_id"]

    try:
        attacker = await get_user_by_id(attacker_id)
        target = await get_user_by_id(target_id)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        await query.edit_message_text("❌ خطا در جنگ", reply_markup=back_keyboard())
        return

    if attacker is None or target is None:
        await query.edit_message_text("❌ کاربر پیدا نشد", reply_markup=back_keyboard())
        return

    if target.meat <= 0 or target.tea <= 0:
        await query.edit_message_text(
            f"❌ <b>حمله لغو شد!</b>\n\n"
            f"🎯 حریف: <b>{target.first_name or 'کاربر'}</b>\n\n"
            f"⚠️ این کاربر گوشت و چای نداره!",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    attacker_name = attacker.first_name or "کاربر"
    target_name = target.first_name or "کاربر"

    worker_count = attacker.workers
    lord_count = target.lords
    brick_count = target.bricks

    if worker_count < 1:
        await query.edit_message_text("❌ کارگر افغانی نداری!", reply_markup=back_keyboard())
        return

    available_lords = min(lord_count, brick_count)
    workers_killed_by_lords = available_lords * 5
    remaining_workers = max(0, worker_count - workers_killed_by_lords)
    actual_workers_killed = min(worker_count, workers_killed_by_lords)

    # صحنه ۱
    await query.edit_message_text(
        f"📜 <b>داستان جنگی بزرگ</b>\n"
        f"<i>فصل اول: آغاز</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌅 <b>سپیده‌دم...</b>\n\n"
        f"در دشتی پهناور، سپاه <b>{attacker_name}</b> آماده‌ی نبرد شد.\n"
        f"<b>{worker_count:,}</b> کارگر افغانی با نیزه و شمشیر، آماده‌ی حمله به قلمرو <b>{target_name}</b> شدن.\n\n"
        f"از آن سو، <b>{target_name}</b> با <b>{lord_count:,}</b> لر و <b>{brick_count:,}</b> آجر آماده‌ی دفاعه.\n\n"
        f"⏳ <i>کارگرها در حال حرکت به سمت قلمرو دشمن...</i>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(4)

    # صحنه ۲
    await query.edit_message_text(
        f"📜 <b>داستان جنگی بزرگ</b>\n"
        f"<i>فصل دوم: راهپیمایی</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚶 <b>سپاه در حرکته...</b>\n\n"
        f"کارگرهای افغانی با پای پیاده، از کوه و دشت گذشتن.\n"
        f"گرد و غبار آسمان رو تاریک کرده.\n\n"
        f"🎯 <b>هدف:</b> قلمرو {target_name}\n"
        f"📍 <b>فاصله:</b> ۱۰ کیلومتر\n\n"
        f"⏳ <i>اولین گروه پیشقراولان دارن نزدیک می‌شن...</i>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(4)

    # صحنه ۳
    await query.edit_message_text(
        f"📜 <b>داستان جنگی بزرگ</b>\n"
        f"<i>فصل سوم: دیده‌بانی</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👁️ <b>دیده‌بانان {target_name} سپاه رو دیدن!</b>\n\n"
        f"🛡️ <b>{lord_count:,} لر</b> با عجله به سنگرها رفتن.\n"
        f"🧱 <b>{brick_count:,} آجر</b> برای پرتاب آماده شد.\n\n"
        f"📯 <i>شیپور جنگ زده شد!</i>\n"
        f"🏰 قلعه‌ی {target_name} در حالت آماده‌باش قرار گرفت.\n\n"
        f"⏳ <i>لحظه‌ی رویارویی نزدیکه...</i>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(4)

    # صحنه ۴
    await query.edit_message_text(
        f"📜 <b>داستان جنگی بزرگ</b>\n"
        f"<i>فصل چهارم: نبرد آغاز شد!</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚔️ <b>اولین برخورد!</b>\n\n"
        f"💥 کارگرهای افغانی به دیوارهای قلعه رسیدن!\n\n"
        f"🛡️ لرها شروع کردن به پرت کردن آجر...\n"
        f"🔪 کارگرها فریاد می‌کشن و حمله می‌کنن...\n\n"
        f"⏳ <i>نبرد در جریانه...</i>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(3)

    # صحنه ۵: کشتار
    if worker_count <= 20:
        step = 1
    elif worker_count <= 50:
        step = 5
    elif worker_count <= 100:
        step = 10
    else:
        step = max(1, worker_count // 20)

    killed_so_far = 0
    battle_events = [
        "💥 برخورد اول! کارگرها با سپر جلو می‌رن!",
        "🪨 سنگ از بالا سرازیر می‌شه!",
        "🏹 تیرها از قلعه پرتاب می‌شن!",
        "🔥 آتش به سمت کارگرها!",
        "💪 کارگرها به دروازه رسیدن!",
        "🩸 زمین از خون رنگین شده!",
        "🗡️ کارگرها با نیزه حمله می‌کنن!",
        "🛡️ لرها سنگرها رو مستحکم کردن!",
        "💀 فریاد کارگرهای زخمی!",
        "⚔️ نبرد تن‌به‌تن!",
    ]

    for i in range(0, worker_count + 1, step):
        killed_so_far = i
        remaining_now = max(0, worker_count - i)
        event = random.choice(battle_events)
        progress = int((i / max(1, worker_count)) * 10)
        progress_bar = "█" * progress + "░" * (10 - progress)

        await query.edit_message_text(
            f"📜 <b>داستان جنگی بزرگ</b>\n"
            f"<i>فصل پنجم: کشتار</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚔️ <b>نبرد در جریانه!</b>\n\n"
            f"{event}\n\n"
            f"📊 <b>آمار زنده:</b>\n"
            f"🔪 کارگرهای زنده: <b>{remaining_now:,}</b>\n"
            f"💀 کشته‌شده: <b>{killed_so_far:,}</b>\n"
            f"🛡️ لرهای باقی‌مونده: <b>{max(0, available_lords - (killed_so_far // 5)):,}</b>\n\n"
            f"[{progress_bar}] {progress*10}%\n\n"
            f"⏳ <i>نبرد ادامه داره...</i>",
            parse_mode=ParseMode.HTML,
        )

        if worker_count <= 50:
            await asyncio.sleep(1)
        elif worker_count <= 100:
            await asyncio.sleep(0.8)
        else:
            await asyncio.sleep(0.6)

    # صحنه ۶
    await query.edit_message_text(
        f"📜 <b>داستان جنگی بزرگ</b>\n"
        f"<i>فصل ششم: پایان کشتار</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🩸 <b>میدون جنگ...</b>\n\n"
        f"💀 <b>{actual_workers_killed:,} کارگر افغانی</b> کشته شدن.\n"
        f"🛡️ <b>{available_lords:,} لر</b> در دفاع از قلمروشون قربانی شدن.\n"
        f"🧱 <b>{available_lords:,} آجر</b> در نبرد مصرف شد.\n\n"
        f"🔪 <b>کارگرهای باقی‌مونده:</b> {remaining_workers:,}\n\n"
        f"⏳ <i>در حال محاسبه‌ی نتیجه‌ی نهایی...</i>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(4)

    # محاسبه دزدی
    stolen_tea = remaining_workers * 3
    stolen_meat = remaining_workers * 1
    stolen_tea = min(stolen_tea, target.tea)
    stolen_meat = min(stolen_meat, target.meat)

    attacker_new_workers = attacker.workers - actual_workers_killed
    if attacker_new_workers < 0:
        attacker_new_workers = 0

    await update_resources(
        attacker_id,
        workers=attacker_new_workers,
        tea=attacker.tea + stolen_tea,
        meat=attacker.meat + stolen_meat,
    )

    await update_resources(
        target_id,
        lords=target.lords - available_lords,
        bricks=target.bricks - available_lords,
        tea=target.tea - stolen_tea,
        meat=target.meat - stolen_meat,
    )

    # صحنه ۷: نتیجه
    if remaining_workers > 0:
        result = (
            f"📜 <b>داستان جنگی بزرگ</b>\n"
            f"<i>فصل پایانی: پیروزی!</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏆 <b>{attacker_name} پیروز شد!</b>\n\n"
            f"🎺 شیپور پیروزی نواخته شد.\n"
            f"کارگرهای باقی‌مونده وارد قلمرو {target_name} شدن و غنائم رو جمع کردن.\n\n"
            f"📊 <b>آمار نبرد:</b>\n"
            f"👤 حمله‌کننده: <b>{attacker_name}</b>\n"
            f"🎯 هدف: <b>{target_name}</b>\n\n"
            f"🔪 کارگرهای فرستاده‌شده: <b>{worker_count:,}</b>\n"
            f"💀 کارگرهای کشته‌شده: <b>{actual_workers_killed:,}</b>\n"
            f"🔪 کارگرهای باقی‌مونده: <b>{remaining_workers:,}</b>\n\n"
            f"🛡️ لرهای قربانی‌شده‌ی هدف: <b>{available_lords:,}</b>\n"
            f"🧱 آجرهای مصرف‌شده: <b>{available_lords:,}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>غنائم جنگی:</b>\n"
            f"🥩 گوشت: <b>+{stolen_meat:,}</b>\n"
            f"🍵 چای: <b>+{stolen_tea:,}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        result = (
            f"📜 <b>داستان جنگی بزرگ</b>\n"
            f"<i>فصل پایانی: شکست!</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💥 <b>حمله شکست خورد!</b>\n\n"
            f"🩸 همه‌ی کارگرهای افغانی قربانی شدن.\n"
            f"قلمرو <b>{target_name}</b> از حمله دفاع کرد.\n\n"
            f"📊 <b>آمار نبرد:</b>\n"
            f"👤 حمله‌کننده: <b>{attacker_name}</b>\n"
            f"🎯 هدف: <b>{target_name}</b>\n\n"
            f"🔪 کارگرهای فرستاده‌شده: <b>{worker_count:,}</b>\n"
            f"💀 <b>همه‌ی کارگرها کشته شدن!</b> 🪦\n\n"
            f"🛡️ لرهای دفاعی هدف: <b>{available_lords:,}</b>\n"
            f"🧱 آجرهای مصرف‌شده‌ی هدف: <b>{available_lords:,}</b>\n\n"
            f"🏆 برنده: <b>{target_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    await query.edit_message_text(result, parse_mode=ParseMode.HTML)

    try:
        await log_report(
            event_type="attack",
            description=f"{attacker_name} به {target_name} حمله کرد",
            user_id=attacker_id,
            target_id=target_id,
        )
        await notify_admins(
            context,
            f"⚔️ <b>حمله جدید!</b>\n\n"
            f"👤 حمله‌کننده: <b>{attacker_name}</b> (<code>{attacker_id}</code>)\n"
            f"🎯 هدف: <b>{target_name}</b> (<code>{target_id}</code>)\n"
            f"🔪 کارگرها: <b>{worker_count:,}</b>\n"
            f"💀 کشته‌شده: <b>{actual_workers_killed:,}</b>\n"
            f"🎁 غنیمت: <b>+{stolen_meat:,} گوشت</b>، <b>+{stolen_tea:,} چای</b>",
        )
    except Exception as exc:
        logger.exception("log attack error: %s", exc)


# ═════════════════════════════════════════════
# راهنما، پروفایل، برترها، منابع
# ═════════════════════════════════════════════
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    owner_id = user.id

    old_panel = context.user_data.get("help_panel_msg_id")
    if old_panel is not None:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=old_panel,
            )
        except Exception:
            pass

    sent = await update.message.reply_text(
        HELP_MENU_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=help_keyboard(owner_id),
        disable_web_page_preview=True,
    )

    context.user_data["help_panel_msg_id"] = sent.message_id
    context.user_data["help_panel_chat_id"] = sent.chat.id

    if "help_timeout_task" in context.user_data:
        try:
            context.user_data["help_timeout_task"].cancel()
        except Exception:
            pass

    task = asyncio.create_task(
        auto_close_help_panel(
            context=context,
            chat_id=sent.chat.id,
            message_id=sent.message_id,
            owner_id=owner_id,
            delay=HELP_TIMEOUT_SECONDS,
        )
    )
    context.user_data["help_timeout_task"] = task


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    target_user_db = None

    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user_db = await get_user_by_id(replied.from_user.id)
        if target_user_db is None and replied.text:
            replied_text = replied.text.strip()
            if replied_text.lstrip("-").isdigit():
                target_user_db, _ = await get_or_create_user_by_id(int(replied_text))

    if target_user_db is None:
        parts = text.split()
        if len(parts) > 1:
            target_str = parts[1]
            if target_str.startswith("@"):
                target_user_db = await get_user_by_username(target_str)
            elif target_str.lstrip("-").isdigit() and len(target_str.lstrip("-")) >= 6:
                try:
                    target_user_db, _ = await get_or_create_user_by_id(int(target_str))
                except Exception:
                    pass

    if target_user_db is None:
        try:
            target_user_db, _ = await get_or_create_user(user.id, user.username, user.first_name)
            await check_daily_food(user.id, update)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            return

    remaining = seconds_remaining(target_user_db)
    text_profile = format_user_profile(target_user_db, remaining)
    await update.message.reply_text(text_profile, parse_mode=ParseMode.HTML)


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
        await check_daily_food(user.id, update)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    hungry_status = ""
    if db_user.hungry_days > 0:
        remaining_days = HUNGRY_DAYS_LIMIT - db_user.hungry_days
        hungry_status = (
            f"\n\n⚠️ <b>گرسنگی:</b> {db_user.hungry_days}/{HUNGRY_DAYS_LIMIT} روز\n"
            f"💀 {remaining_days} روز دیگه تا مرگ جنگجوها!"
        )

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
        f"🌟 پسر خوب: <b>{db_user.pad_boy:,}</b>\n\n"
        f"⚔️ <b>جنگجوها:</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers:,}</b>\n"
        f"🛡️ لر: <b>{db_user.lords:,}</b>"
        f"{hungry_status}",
        parse_mode=ParseMode.HTML,
    )


# ═════════════════════════════════════════════
# حمله
# ═════════════════════════════════════════════
async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    try:
        attacker, _ = await get_or_create_user(user.id, user.username, user.first_name)
        await check_daily_food(user.id, update)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if attacker.workers < 1:
        await update.message.reply_text(
            "❌ کارگر افغانی نداری! از فروشگاه بخر.",
            parse_mode=ParseMode.HTML,
        )
        return

    target_user = None

    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user = await get_user_by_id(replied.from_user.id)
        if target_user is None and replied.text:
            replied_text = replied.text.strip()
            if replied_text.lstrip("-").isdigit():
                target_user, _ = await get_or_create_user_by_id(int(replied_text))

    if target_user is None:
        parts = text.split()
        for part in parts[1:]:
            if part.startswith("@"):
                target_user = await get_user_by_username(part)
                if target_user is not None:
                    break
            elif part.lstrip("-").isdigit() and len(part.lstrip("-")) >= 6:
                try:
                    target_user, _ = await get_or_create_user_by_id(int(part))
                    if target_user is not None:
                        break
                except Exception:
                    pass

    if target_user is None:
        await update.message.reply_text(
            "❌ حریف پیدا نشد!\n\n"
            "📋 روش‌های درست:\n"
            "1️⃣ روی پیام کاربر <b>ریپلای</b> کن و بنویس <code>حمله</code>\n"
            "2️⃣ <code>حمله @username</code>\n"
            "3️⃣ <code>حمله 123456789</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if target_user.telegram_id == user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت حمله کنی!")
        return

    if target_user.meat <= 0 or target_user.tea <= 0:
        await update.message.reply_text(
            f"❌ <b>حمله لغو شد!</b>\n\n"
            f"🎯 حریف: <b>{target_user.first_name or 'کاربر'}</b>\n\n"
            f"⚠️ این کاربر گوشت و چای نداره!\n"
            f"🥩 گوشت: <b>{target_user.meat:,}</b>\n"
            f"🍵 چای: <b>{target_user.tea:,}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_name = target_user.first_name or target_user.username or "کاربر"

    keyboard = [[
        InlineKeyboardButton(
            "📝 ثبت درخواست حمله",
            callback_data=f"war_request_{target_user.telegram_id}",
            style="danger",
        ),
        InlineKeyboardButton("❌ لغو", callback_data="war_cancel", style="success"),
    ]]

    await update.message.reply_text(
        f"⚔️ <b>درخواست حمله</b>\n\n"
        f"👤 حمله‌کننده: <b>{attacker.first_name}</b>\n"
        f"🎯 هدف: <b>{target_name}</b>\n\n"
        f"🔪 کارگرهای افغانی تو: <b>{attacker.workers:,}</b>\n"
        f"🛡️ لرهای حریف: <b>{target_user.lords:,}</b>\n"
        f"🧱 آجرهای حریف: <b>{target_user.bricks:,}</b>\n\n"
        f"⚠️ آیا از حمله مطمئنی؟",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ═════════════════════════════════════════════
# پرت سیفید
# ═════════════════════════════════════════════
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
            target_user = await get_user_by_id(int(target_str))
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


# ═════════════════════════════════════════════
# انتقال
# ═════════════════════════════════════════════
async def admin_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "<code>انتقال [منبع] [تعداد] [آی‌دی/یوزرنیم]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    resource_name = None
    amount = None
    target_offset = None

    two_word_resources = ["نون بربری", "کیک یزدی", "کارگر افغانی", "گل رز", "دختر خوب", "پسر خوب"]
    two_word_found = False

    for res in two_word_resources:
        res_parts = res.split()
        if len(parts) >= 2 + len(res_parts):
            if parts[1:1 + len(res_parts)] == res_parts:
                resource_name = res
                try:
                    amount = int(parts[1 + len(res_parts)])
                    target_offset = 2 + len(res_parts)
                    two_word_found = True
                except (ValueError, IndexError):
                    pass
                break

    if not two_word_found and len(parts) >= 3:
        resource_name = parts[1]
        try:
            amount = int(parts[2])
            target_offset = 3
        except ValueError:
            pass

    if resource_name is None or amount is None:
        await update.message.reply_text("❌ فرمت اشتباه!", parse_mode=ParseMode.HTML)
        return

    if resource_name not in RESOURCE_MAP:
        await update.message.reply_text(
            f"❌ منبع <b>{resource_name}</b> شناخته نشد!",
            parse_mode=ParseMode.HTML,
        )
        return

    if amount <= 0:
        await update.message.reply_text("❌ تعداد باید یه عدد مثبت باشه!")
        return

    target_user = None

    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user, _ = await get_or_create_user_by_id(replied.from_user.id)
        elif replied.text and replied.text.strip().isdigit():
            target_user, _ = await get_or_create_user_by_id(int(replied.text.strip()))

    if target_user is None and len(parts) > target_offset:
        target_str = parts[target_offset]
        if target_str.startswith("@"):
            target_user = await get_user_by_username(target_str)
        elif target_str.lstrip("-").isdigit():
            target_user, _ = await get_or_create_user_by_id(int(target_str))

    if target_user is None:
        await update.message.reply_text("❌ کاربر پیدا نشد!", parse_mode=ParseMode.HTML)
        return

    column = RESOURCE_MAP[resource_name]
    receiver_current = getattr(target_user, column)
    receiver_new = receiver_current + amount

    await update_resources(target_user.telegram_id, **{column: receiver_new})

    target_name = target_user.first_name or target_user.username or "کاربر"

    await update.message.reply_text(
        f"✅ <b>{amount:,} {resource_name}</b> به <b>{target_name}</b> منتقل شد!\n\n"
        f"📦 موجودی جدید گیرنده: <b>{receiver_new:,}</b>\n"
        f"♾️ موجودی تو: <b>بی‌نهایت</b>",
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
        logger.exception("send_message error: %s", exc)

    try:
        await log_report(
            event_type="admin_transfer",
            description=f"انتقال {amount:,} {resource_name} به {target_name}",
            user_id=user.id,
            target_id=target_user.telegram_id,
        )
        await notify_admins(
            context,
            f"📤 <b>انتقال مدیر</b>\n\n"
            f"👤 از: <b>{user.first_name}</b>\n"
            f"🎯 به: <b>{target_name}</b> (<code>{target_user.telegram_id}</code>)\n"
            f"📦 منبع: <b>{resource_name}</b>\n"
            f"💎 مقدار: <b>{amount:,}</b>",
        )
    except Exception as exc:
        logger.exception("log admin_transfer error: %s", exc)


async def admin_remove_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "<code>حذف انتقال [منبع] [تعداد] [آی‌دی/یوزرنیم]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    resource_name = None
    amount = None
    target_offset = None

    two_word_resources = ["نون بربری", "کیک یزدی", "کارگر افغانی", "گل رز", "دختر خوب", "پسر خوب"]
    two_word_found = False

    for res in two_word_resources:
        res_parts = res.split()
        if len(parts) >= 3 + len(res_parts):
            if parts[2:2 + len(res_parts)] == res_parts:
                resource_name = res
                try:
                    amount = int(parts[2 + len(res_parts)])
                    target_offset = 3 + len(res_parts)
                    two_word_found = True
                except (ValueError, IndexError):
                    pass
                break

    if not two_word_found and len(parts) >= 4:
        resource_name = parts[2]
        try:
            amount = int(parts[3])
            target_offset = 4
        except ValueError:
            pass

    if resource_name is None or amount is None:
        await update.message.reply_text("❌ فرمت اشتباه!", parse_mode=ParseMode.HTML)
        return

    if resource_name not in RESOURCE_MAP:
        await update.message.reply_text(f"❌ منبع شناخته نشد!", parse_mode=ParseMode.HTML)
        return

    if amount <= 0:
        await update.message.reply_text("❌ تعداد باید مثبت باشه!")
        return

    target_user = None

    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user, _ = await get_or_create_user_by_id(replied.from_user.id)
        elif replied.text and replied.text.strip().isdigit():
            target_user, _ = await get_or_create_user_by_id(int(replied.text.strip()))

    if target_user is None and len(parts) > target_offset:
        target_str = parts[target_offset]
        if target_str.startswith("@"):
            target_user = await get_user_by_username(target_str)
        elif target_str.lstrip("-").isdigit():
            target_user, _ = await get_or_create_user_by_id(int(target_str))

    if target_user is None:
        await update.message.reply_text("❌ کاربر پیدا نشد!", parse_mode=ParseMode.HTML)
        return

    column = RESOURCE_MAP[resource_name]
    receiver_current = getattr(target_user, column)
    receiver_new = receiver_current - amount

    await update_resources(target_user.telegram_id, **{column: receiver_new})

    target_name = target_user.first_name or target_user.username or "کاربر"

    await update.message.reply_text(
        f"✅ <b>{amount:,} {resource_name}</b> از <b>{target_name}</b> پس گرفته شد!\n\n"
        f"📦 موجودی جدید گیرنده: <b>{receiver_new:,}</b>",
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
        logger.exception("send_message error: %s", exc)

    try:
        await log_report(
            event_type="admin_remove_transfer",
            description=f"پس گرفتن {amount:,} {resource_name} از {target_name}",
            user_id=user.id,
            target_id=target_user.telegram_id,
        )
        await notify_admins(
            context,
            f"📥 <b>پس گرفتن مدیر</b>\n\n"
            f"👤 از: <b>{target_name}</b> (<code>{target_user.telegram_id}</code>)\n"
            f"📦 منبع: <b>{resource_name}</b>\n"
            f"💎 مقدار: <b>{amount:,}</b>",
        )
    except Exception as exc:
        logger.exception("log admin_remove error: %s", exc)


# ═════════════════════════════════════════════
# خروج
# ═════════════════════════════════════════════
async def leave_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "از طرف سازنده‌ها، ربات داره از این گروه می‌ره. 🌹",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Send goodbye error: %s", exc)

    try:
        await context.bot.leave_chat(chat_id=chat.id)
    except Exception as exc:
        logger.exception("leave_chat error: %s", exc)


# ═════════════════════════════════════════════
# هندلر اصلی
# ═════════════════════════════════════════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if user is None:
        return

    buying = context.user_data.get("buying")
    if buying is not None and "amount" not in buying and text.isdigit():
        await process_buy_amount(update, context, int(text))
        return

    # راهنما
    if text == CMD_HELP:
        await help_handler(update, context)
        return

    # پروفایل
    if text == CMD_PROFILE or text.startswith("پروفایل "):
        await profile_handler(update, context)
        return

    # فروشگاه (🆕)
    if text in ("فروشگاه", "فروشگاه شومپد", "شومپد فروشگاه"):
        await shop_handler(update, context)
        return

    if text in (CMD_TOP, "برتر"):
        await top_handler(update, context)
        return
    if text == CMD_RESOURCES:
        await resources_handler(update, context)
        return
    if text == CMD_REPORT:
        if user.id not in ADMIN_IDS:
            return
        await report_handler(update, context)
        return
    if text.startswith("پرت سیفید"):
        await transfer_shield_handler(update, context)
        return

    if text == "خروج":
        if user.id not in ADMIN_IDS:
            return
        await leave_group_handler(update, context)
        return

    if text == "حمله" or text.startswith("حمله ") or text.startswith("حمله‌"):
        await attack_handler(update, context)
        return

    if text.startswith("حذف انتقال"):
        if user.id not in ADMIN_IDS:
            return
        await admin_remove_transfer_handler(update, context)
        return

    if text.startswith("انتقال"):
        if user.id not in ADMIN_IDS:
            return
        await admin_transfer_handler(update, context)
        return

    if text not in KEYWORDS:
        return

    points, required_pads = KEYWORDS[text]

    try:
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        await check_daily_food(user.id, update)
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
