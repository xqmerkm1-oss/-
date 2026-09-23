import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import (
    attack_keyboard,
    back_keyboard,
    help_keyboard,
    shop_keyboard,
    start_keyboard,
)
from messages import HELP_TEXT, START_TEXT
from repository import (
    add_pads,
    get_or_create_user,
    get_random_user_in_group,
    get_top_users,
    get_user_by_id,
    get_user_by_username,
    give_reward,
    increment_invite_count,
    mark_bread_used,
    seconds_remaining,
    transfer_shields,
    update_resources,
)

logger = logging.getLogger(__name__)


CHANNEL_ID = -1004372622419
CHANNEL_LINK = "https://t.me/SchompedCanal"
BOT_USERNAME = "Schompedbot"

INVITER_REWARD = 500
INVITED_REWARD = 250


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
CMD_RESOURCES = "منابع"
CMD_ATTACK = "حمله"


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

    # ─── حساب من ───
    if data == "menu_profile":
        try:
            db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
        except Exception as exc:
            logger.exception("DB error: %s", exc)
            await query.edit_message_text("❌ خطا در دریافت اطلاعات.", reply_markup=back_keyboard())
            return

        remaining = seconds_remaining(db_user)
        if remaining > 0:
            minutes = remaining // 60
            secs = remaining % 60
            cooldown = f"⏳ {minutes} دقیقه و {secs} ثانیه" if minutes > 0 else f"⏳ {secs} ثانیه"
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
            f"🎁 تعداد دعوت: <b>{db_user.invite_count}</b>\n"
            f"⏳ وضعیت جایزه: {cooldown}\n\n"
            f"{unlock_status}{bread_status}",
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
            f"🥖 نون بربری: <b>{db_user.bread_count}</b>\n"
            f"🧱 آجر: <b>{db_user.bricks}</b>\n"
            f"🍰 کیک یزدی: <b>{db_user.cake}</b>\n\n"
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
                f"❌ نون بربری کافی نداری!\nنیاز: ۱۰۰\nموجودی: {db_user.bread_count}",
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
                f"❌ آجر کافی نداری!\nنیاز: ۵۰\nموجودی: {db_user.bricks}",
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
                f"❌ نون بربری کافی نداری!\nنیاز: ۱۰\nموجودی: {db_user.bread_count}",
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
            lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پد")

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

    # ─── تایید حمله ───
    if data.startswith("attack_confirm_"):
        try:
            target_id = int(data.replace("attack_confirm_", ""))
        except ValueError:
            await query.answer("❌ خطا", show_alert=True)
            return

        await execute_attack(update, context, user, target_id)
        return

    if data == "attack_cancel":
        await query.edit_message_text(
            "❌ حمله لغو شد.",
            reply_markup=back_keyboard(),
        )
        return


# ─────────────────────────────────────────────
# راهنما، پروفایل، برترها، منابع، حمله
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
        db_user, _ = await get_or_create_user(user.id, user.username, user.first_name)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        return

    remaining = seconds_remaining(db_user)
    if remaining > 0:
        minutes = remaining // 60
        secs = remaining % 60
        cooldown = f"⏳ {minutes} دقیقه و {secs} ثانیه" if minutes > 0 else f"⏳ {secs} ثانیه"
    else:
        cooldown = "✅ آماده"

    name = db_user.first_name or "دوست عزیز"
    username = f"@{db_user.username}" if db_user.username else "ندارد"

    await update.message.reply_text(
        f"👤 <b>حساب من</b>\n\n"
        f"📛 نام: <b>{name}</b>\n"
        f"🆔 آی‌دی عددی: <code>{db_user.telegram_id}</code>\n"
        f"🔗 یوزرنیم: <b>{username}</b>\n"
        f"💎 پدها: <b>{db_user.pads}</b>\n"
        f"🎁 تعداد دعوت: <b>{db_user.invite_count}</b>\n"
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
        lines.append(f"{medals[i]} <b>{name}</b> — {u.pads} پد")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


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
        f"🥩 گوشت: <b>{db_user.meat}</b>\n"
        f"🍵 چای: <b>{db_user.tea}</b>\n"
        f"🧱 آجر: <b>{db_user.bricks}</b>\n"
        f"🥖 نون بربری: <b>{db_user.bread_count}</b>\n"
        f"🍰 کیک یزدی: <b>{db_user.cake}</b>\n"
        f"🔪 سیفید: <b>{db_user.shields}</b>\n\n"
        f"⚔️ <b>جنگجوها:</b>\n"
        f"🔪 کارگر افغانی: <b>{db_user.workers}</b>\n"
        f"🛡️ لر: <b>{db_user.lords}</b>",
        parse_mode=ParseMode.HTML,
    )


async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "🔒 بخش جنگ وقتی <b>شمع</b> برات باز بشه فعال می‌شه! (۶۰۰۰ پد)",
            parse_mode=ParseMode.HTML,
        )
        return

    if db_user.workers < 1:
        await update.message.reply_text(
            "❌ کارگر افغانی نداری! از فروشگاه بخر.",
            parse_mode=ParseMode.HTML,
        )
        return

    target = await get_random_user_in_group(context, update.effective_chat.id, user.id)
    if target is None:
        await update.message.reply_text("❌ کسی برای حمله پیدا نشد!")
        return

    target_name = target.first_name or target.username or "کاربر"

    await update.message.reply_text(
        f"⚔️ <b>آماده‌ی حمله به {target_name} هستی!</b>\n\n"
        f"🔪 کارگرهای افغانی تو: <b>{db_user.workers}</b>\n"
        f"🛡️ لرهای حریف: <b>{target.lords}</b>\n\n"
        f"تایید می‌کنی؟",
        parse_mode=ParseMode.HTML,
        reply_markup=attack_keyboard(target.telegram_id),
    )


async def execute_attack(update, context, user, target_id: int) -> None:
    query = update.callback_query

    try:
        attacker, _ = await get_or_create_user(user.id, user.username, user.first_name)
        defender = await get_user_by_id(target_id)
    except Exception as exc:
        logger.exception("DB error: %s", exc)
        await query.edit_message_text("❌ خطا در حمله.", reply_markup=back_keyboard())
        return

    if defender is None:
        await query.edit_message_text("❌ حریف پیدا نشد.", reply_markup=back_keyboard())
        return

    workers = attacker.workers
    lords = defender.lords
    bricks_thrown = lords * 14

    if lords >= workers * 1.4:
        await update_resources(user.id, workers=0)
        await query.edit_message_text(
            f"💥 <b>حمله شکست خورد!</b>\n\n"
            f"🛡️ لرهای حریف <b>{bricks_thrown}</b> آجر پرت کردن!\n"
            f"🔪 تمام <b>{workers}</b> کارگر افغانی تو کشته شدن. 🪦",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        return

    stolen_meat = min(50, defender.meat)
    stolen_tea = min(25, defender.tea)

    await update_resources(
        user.id,
        workers=0,
        meat=attacker.meat + stolen_meat,
        tea=attacker.tea + stolen_tea,
    )
    await update_resources(
        target_id,
        meat=defender.meat - stolen_meat,
        tea=defender.tea - stolen_tea,
    )

    await query.edit_message_text(
        f"🎉 <b>حمله موفق!</b>\n\n"
        f"🥩 <b>{stolen_meat}</b> گوشت دزدیدی!\n"
        f"🍵 <b>{stolen_tea}</b> چای دزدیدی!\n\n"
        f"🔪 <b>{workers}</b> کارگر افغانی تو قربانی شدن.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard(),
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
            f"❌ سیفید کافی نداری!\nموجودی: <b>{sender.shields}</b>",
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
            f"🎁 <b>{amount} سیفید</b> به <b>{target_name}</b> پرت کردی!",
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
    if text == CMD_RESOURCES:
        await resources_handler(update, context)
        return
    if text == CMD_ATTACK:
        await attack_handler(update, context)
        return
    if text.startswith("پرت سیفید"):
        await transfer_shield_handler(update, context)
        return

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
            f"💎 پدهای فعلی: <b>{db_user.pads}</b>\n"
            f"🎯 نیاز: <b>{required_pads}</b> پد\n"
            f"📉 <b>{needed} پد</b> دیگه لازم داری.",
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

    if text == "نون بربری":
        await update_resources(user.id, bread_count=updated.bread_count + 5)
    elif text == "آجر":
        await update_resources(user.id, bricks=updated.bricks + 5)
    elif text == "سیفید":
        await update_resources(user.id, shields=updated.shields + 5)

    bread_msg = ""
    if text == "نون بربری":
        await mark_bread_used(user.id)
        bread_msg = "\n\n⚠️ از این به بعد <b>دختر خوب</b> و <b>پسر خوب</b> برات قفل شده!"

    await update.message.reply_text(
        f"🎉 <b>{points} {text} پد گرفتی</b>\n\n"
        f"💎 پد هات : <b>{updated.pads}</b>\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری{bread_msg}",
        parse_mode=ParseMode.HTML,
    )
