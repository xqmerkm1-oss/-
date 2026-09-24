import asyncio
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

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


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
        f"🛡️ لر: <b>{db_user.lords:,}</b>\n\n"
        f"🎁 تعداد دعوت: <b>{db_user.invite_count}</b>\n"
        f"⏳ وضعیت جایزه: {cooldown}\n\n"
        f"📅 تاریخ: <b>{date_str}</b>\n"
        f"🕐 ساعت: <b>{time_str}</b> (تهران)"
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
            f"💼 موجودی تو: <b>{user_balance:,} {price_name}</b>\n\n"
            f"📉 <b>{total_price - user_balance:,} {price_name}</b> دیگه لازم داری.",
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

    if data == "menu_close":
        try:
            await query.message.delete()
        except Exception as exc:
            logger.exception("Delete error: %s", exc)
        return

    # ─── راهنما ───
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
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا", reply_markup=back_keyboard())
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

    if data == "shop_buy_worker":
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

    if data == "shop_buy_lord":
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

    if data == "shop_buy_cake":
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
                f"❌ <b>موجودی کافی نداری!</b>\n\n"
                f"💰 هزینه کل: <b>{total_price:,}</b>\n"
                f"💼 موجودی تو: <b>{user_balance:,}</b>",
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

    if data == "cancel_buy":
        context.user_data.pop("buying", None)
        await query.edit_message_text("❌ خرید لغو شد.", reply_markup=back_keyboard())
        return

    # ─── ثبت درخواست حمله ───
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

        target_name = target_user.first_name or target_user.username or "کاربر"

        # ذخیره توی context
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
            f"⚠️ آیا از حمله مطمئنی؟\n"
            f"با تایید، جنگ شروع می‌شه.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ─── لغو حمله ───
    if data == "war_cancel":
        context.user_data.pop("war", None)
        await query.edit_message_text("❌ حمله لغو شد.", reply_markup=back_keyboard())
        return

    # ─── تایید و اجرای جنگ ───
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
# اجرای جنگ (نمایش لحظه‌ای)
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

    attacker_name = attacker.first_name or "کاربر"
    target_name = target.first_name or "کاربر"

    worker_count = attacker.workers

    if worker_count < 1:
        await query.edit_message_text("❌ کارگر افغانی نداری!", reply_markup=back_keyboard())
        return

    # ─── مرحله ۱: شروع ───
    await query.edit_message_text(
        f"⚔️ <b>جنگ شروع شد!</b>\n\n"
        f"👤 <b>{attacker_name}</b> با <b>{worker_count:,}</b> کارگر افغانی حمله کرد!\n"
        f"🎯 هدف: <b>{target_name}</b>\n\n"
        f"🛡️ لرهای مدافع: <b>{target.lords:,}</b>\n"
        f"🧱 آجرهای مدافع: <b>{target.bricks:,}</b>\n\n"
        f"⏳ در حال نبرد...",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(2)

    # ─── مرحله ۲: رسیدن کارگرها ───
    await query.edit_message_text(
        f"⚔️ <b>جنگ در جریانه!</b>\n\n"
        f"👤 <b>{attacker_name}</b> با <b>{worker_count:,}</b> کارگر افغانی حمله کرد!\n"
        f"🎯 هدف: <b>{target_name}</b>\n\n"
        f"🔪 کارگرهای افغانی دارن می‌رسن...\n"
        f"🛡️ <b>{target.lords:,} لر</b> آماده‌ی دفاع شدن!\n\n"
        f"⏳ در حال نبرد...",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(2)

    # ─── محاسبه نتیجه ───
    available_lords = min(target.lords, target.bricks)
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
    stolen_tea = min(stolen_tea, target.tea)
    stolen_meat = min(stolen_meat, target.meat)

    # ─── مرحله ۳: نمایش دفاع ───
    battle_lines = [
        f"⚔️ <b>نبرد در جریان!</b>\n",
        f"👤 حمله‌کننده: <b>{attacker_name}</b>",
        f"🎯 هدف: <b>{target_name}</b>\n",
    ]

    if available_lords > 0:
        battle_lines.append(f"🛡️ <b>{available_lords:,} لر</b> از {target_name} دفاع کردن!")
        battle_lines.append(f"💀 <b>{worker_count - remaining_workers:,} کارگر</b> کشته شدن!")
        battle_lines.append(f"🧱 <b>{available_lords:,} آجر</b> مصرف شد!\n")
    else:
        battle_lines.append(f"⚠️ {target_name} هیچ لر یا آجری برای دفاع نداشت!\n")

    battle_lines.append(f"🔪 کارگرهای باقی‌مونده: <b>{remaining_workers:,}</b>")
    battle_lines.append(f"⏳ در حال محاسبه‌ی نتیجه...")

    await query.edit_message_text("\n".join(battle_lines), parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)

    # ─── به‌روزرسانی دیتابیس ───
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

    # ─── مرحله ۴: نتیجه نهایی ───
    if remaining_workers > 0:
        result = (
            f"🎉 <b>جنگ تموم شد!</b>\n"
            f"🏆 <b>{attacker_name}</b> برنده شد!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 حمله‌کننده: <b>{attacker_name}</b>\n"
            f"🎯 هدف: <b>{target_name}</b>\n\n"
            f"🔪 کارگرهای فرستاده‌شده: <b>{worker_count:,}</b>\n"
            f"💀 کارگرهای کشته‌شده: <b>{worker_count - remaining_workers:,}</b>\n"
            f"🔪 کارگرهای باقی‌مونده: <b>{remaining_workers:,}</b>\n\n"
            f"🛡️ لرهای مصرف‌شده‌ی هدف: <b>{available_lords:,}</b>\n"
            f"🧱 آجرهای مصرف‌شده‌ی هدف: <b>{available_lords:,}</b>\n\n"
            f"🎁 <b>غنیمت:</b>\n"
            f"🥩 گوشت: <b>+{stolen_meat:,}</b>\n"
            f"🍵 چای: <b>+{stolen_tea:,}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        result = (
            f"💥 <b>حمله شکست خورد!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 حمله‌کننده: <b>{attacker_name}</b>\n"
            f"🎯 هدف: <b>{target_name}</b>\n\n"
            f"🔪 کارگرهای فرستاده‌شده: <b>{worker_count:,}</b>\n"
            f"💀 همه‌ی کارگرها کشته شدن! 🪦\n\n"
            f"🛡️ لرهای دفاعی هدف: <b>{available_lords:,}</b>\n"
            f"🧱 آجرهای مصرف‌شده‌ی هدف: <b>{available_lords:,}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    await query.edit_message_text(result, parse_mode=ParseMode.HTML)


# ═════════════════════════════════════════════
# دستورات متنی
# ═════════════════════════════════════════════
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
        f"🛡️ لر: <b>{db_user.lords:,}</b>",
        parse_mode=ParseMode.HTML,
    )


# ═════════════════════════════════════════════
# حمله با ریپلای
# ═════════════════════════════════════════════
async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حمله.
    
    روش‌ها:
    - حمله (با ریپلای)
    - حمله @user (با ریپلای)
    - حمله 123456789 (با ریپلای)
    """
    if update.message is None or update.effective_user is None:
        return

    user = update.effective_user
    text = update.message.text.strip()

    try:
        attacker, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    if attacker.workers < 1:
        await update.message.reply_text(
            "❌ کارگر افغانی نداری! از فروشگاه بخر.",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── پیدا کردن حریف ───
    target_user = None

    # ۱. ریپلای روی پیام کاربر
    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user = await get_user_by_id(replied.from_user.id)

    # ۲. اگه ریپلای نبود، توی متن بگرد
    if target_user is None:
        parts = text.split()
        for part in parts[1:]:
            if part.startswith("@"):
                target_user = await get_user_by_username(part)
                if target_user is not None:
                    break
            elif part.lstrip("-").isdigit() and len(part) > 5:
                try:
                    target_user = await get_user_by_id(int(part))
                    if target_user is not None:
                        break
                except Exception:
                    pass

    if target_user is None:
        await update.message.reply_text(
            "❌ حریف پیدا نشد!\n\n"
            "📋 روش‌های درست:\n"
            "1️⃣ روی پیام کاربر <b>ریپلای</b> کن و بنویس <code>حمله</code>\n"
            "2️⃣ یا <code>حمله @user</code> با ریپلای\n"
            "3️⃣ یا <code>حمله 123456789</code> با ریپلای",
            parse_mode=ParseMode.HTML,
        )
        return

    if target_user.telegram_id == user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت حمله کنی!")
        return

    target_name = target_user.first_name or target_user.username or "کاربر"

    # ─── پیام درخواست حمله ───
    keyboard = [[
        InlineKeyboardButton("📝 ثبت درخواست حمله", callback_data=f"war_request_{target_user.telegram_id}", style="danger"),
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
# انتقال توسط سازنده‌ها
# ═════════════════════════════════════════════
async def admin_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتقال منابع توسط سازنده‌ها.
    
    فرمت‌ها:
    - انتقال پد 1000 1844792522
    - انتقال پد 1000 @ali
    - انتقال پد 1000  (با ریپلای)
    """
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
            "<code>انتقال [منبع] [تعداد]</code> + ریپلای",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── پیدا کردن منبع ───
    resource_name = None
    amount = None
    target_offset = None

    # منابع دو کلمه‌ای
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

    # منابع تک کلمه‌ای
    if not two_word_found and len(parts) >= 3:
        resource_name = parts[1]
        try:
            amount = int(parts[2])
            target_offset = 3
        except ValueError:
            pass

    if resource_name is None or amount is None:
        await update.message.reply_text(
            "❌ فرمت اشتباه!\n\n"
            "📋 مثال:\n"
            "<code>انتقال پد 1000 1844792522</code>\n"
            "<code>انتقال پد 1000</code> + ریپلای",
            parse_mode=ParseMode.HTML,
        )
        return

    if resource_name not in RESOURCE_MAP:
        await update.message.reply_text(
            f"❌ منبع <b>{resource_name}</b> شناخته نشد!\n\n"
            f"📋 منابع معتبر:\n"
            f"<code>پد، گوشت، چای، آجر، نون بربری، کیک یزدی، سیفید،\n"
            f"کارگر افغانی، لر، گل رز، دختر خوب، پسر خوب</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if amount <= 0:
        await update.message.reply_text("❌ تعداد باید یه عدد مثبت باشه!")
        return

    # ─── پیدا کردن هدف ───
    target_user = None

    # ۱. ریپلای
    if update.message.reply_to_message is not None:
        replied = update.message.reply_to_message
        if replied.from_user is not None and not replied.from_user.is_bot:
            target_user, _ = await get_or_create_user_by_id(replied.from_user.id)
        elif replied.text and replied.text.strip().isdigit():
            target_user, _ = await get_or_create_user_by_id(int(replied.text.strip()))

    # ۲. متن
    if target_user is None and len(parts) > target_offset:
        target_str = parts[target_offset]
        if target_str.startswith("@"):
            target_user = await get_user_by_username(target_str)
        elif target_str.lstrip("-").isdigit():
            target_user, _ = await get_or_create_user_by_id(int(target_str))

    if target_user is None:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد!\n\n"
            "📋 روش‌های درست:\n"
            "1️⃣ <code>انتقال پد 1000 1844792522</code>\n"
            "2️⃣ <code>انتقال پد 1000 @ali</code>\n"
            "3️⃣ <code>انتقال پد 1000</code> + ریپلای روی پیام کاربر",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── انتقال ───
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

    # ─── پیدا کردن منبع ───
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
        await update.message.reply_text(f"❌ منبع <b>{resource_name}</b> شناخته نشد!", parse_mode=ParseMode.HTML)
        return

    if amount <= 0:
        await update.message.reply_text("❌ تعداد باید یه عدد مثبت باشه!")
        return

    # ─── پیدا کردن هدف ───
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


# ═════════════════════════════════════════════
# خروج از گروه
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


# ═════════════════════════════════════════════
# هندلر اصلی متن
# ═════════════════════════════════════════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if user is None:
        return

    # خرید
    buying = context.user_data.get("buying")
    if buying is not None and "amount" not in buying and text.isdigit():
        await process_buy_amount(update, context, int(text))
        return

    # دستورات
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

    # خروج
    if text == "خروج":
        if user.id not in ADMIN_IDS:
            return
        await leave_group_handler(update, context)
        return

    # حمله
    if text == "حمله" or text.startswith("حمله ") or text.startswith("حمله‌"):
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
