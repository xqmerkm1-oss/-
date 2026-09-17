import os
import html
import asyncio
import logging
from datetime import datetime

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import (
    init_db,
    save_user,
    save_gender_info,
    get_user_count,
    get_user_info,
    get_shombool,
    add_shombool,
    get_last_claim,
    set_last_claim,
    get_top_shombool,
)

# ---------- تنظیمات ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

# ⚙️ تنظیمات شومبول
SHOMBOOL_AMOUNT = 5           # مقدار هر دریافت
SHOMBOOL_COOLDOWN = 60        # ثانیه

# 📝 متن استارت
START_TEXT = os.getenv(
    "START_TEXT",
    """سلام {mention} 👋
شنیدم دلت شومبول می‌خواد 🍌
تو می‌تونی یه کصخل بامزه باشی برای به‌گایی‌هات برای ایران 🤡

🎯 شومبول و نازسرین جمع کن تا بتونی کصخل بهتری باشی

━━━━━━━━━━━━━━━
😎 شمارو بعضی وقتا به تخممون می‌گیریم
📈 عملکرد خوب که نه، ولی تو می‌تونی کصخل نیو داشته باشی
🔄 آپدیت‌های سالیانه میدیم بیرون
🤝 مثل شما می‌تونیم یه کصخل باشیم
🕐 پشتیبانی ۲۶ ساعته
💰 کاملاً رایگان — بعضی وقتا پولی 😏"""
)

# 🎉 متن خوش‌آمد گروه
WELCOME_TEXT = """🎉 <b>یه جقی وارد گروه شده</b> 🍌
پاشید <b>جق بزنید</b> 💦✊

━━━━━━━━━━━━━━━
🍌 برای دریافت شومبول بنویسید: <b>شومبول</b>
🏆 برترین‌ها رو از دکمه‌ها ببینید 👇
"""

# 📖 متن توضیحات کوتاه
INFO_TEXT = """📖 <b>توضیحات کوتاه</b>

🍌 <b>شومبول چیه؟</b>
یه واحد پول خنده‌دار که با نوشتن کلمه‌ی «شومبول» توی گروه به دست میاد!

⚙️ <b>چطور کار می‌کنه؟</b>
• توی گروه بنویس: <b>شومبول</b>
• هر بار <b>۵ شومبول متوسط</b> می‌گیری
• هر <b>۱ دقیقه</b> یه بار می‌تونی درخواست کنی

🎯 <b>جنبه چیه؟</b>
• <b>با جنبه‌ها</b> می‌تونن از <b>۱۰۰٪</b> ربات استفاده کنن
• <b>بی‌جنبه‌ها</b> فقط از یه چیزای کمش 😏

🏆 <b>برترین‌ها</b>
با جمع کردن شومبول، اسمت میره توی لیست برترین‌ها!

━━━━━━━━━━━━━━━
💡 برای شروع، جنسیتت رو انتخاب کن 👇
"""

# 📝 متن سوال جنسیت
GENDER_QUESTION = """🎭 <b>جنسیتت چیه؟</b>

یه توضیح کوتاه:
• اگه <b>دختری و جنبه داری</b> → بزن رو «👧 دخترم، جنبه دارم»
• اگه <b>دختری و جنبه نداری</b> → بزن رو «👧 دخترم، جنبه ندارم»
• اگه <b>پسری و جنبه داری</b> → بزن رو «👦 پسرم، جنبه دارم»
• اگه <b>پسری و جنبه نداری</b> → بزن رو «👦 پسرم، جنبه ندارم»

━━━━━━━━━━━━━━━
✅ <b>با جنبه‌ها</b> می‌تونن از <b>۱۰۰٪</b> ربات استفاده کنن
❌ <b>بی‌جنبه‌ها</b> فقط از یه چیزای کمش 😏

الان انتخاب کن 👇"""


# ---------- کمکی ----------
def _format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "الان"
    m, s = divmod(seconds, 60)
    if m and s:
        return f"<b>{m}</b> دقیقه و <b>{s}</b> ثانیه"
    elif m:
        return f"<b>{m}</b> دقیقه"
    else:
        return f"<b>{s}</b> ثانیه"


def _gender_keyboard():
    """کیبورد ۴ دکمه‌ای جنسیت."""
    keyboard = [
        [
            InlineKeyboardButton("👧 دخترم، جنبه دارم", callback_data="g_girl_yes"),
            InlineKeyboardButton("👧 دخترم، جنبه ندارم", callback_data="g_girl_no"),
        ],
        [
            InlineKeyboardButton("👦 پسرم، جنبه دارم", callback_data="g_boy_yes"),
            InlineKeyboardButton("👦 پسرم، جنبه ندارم", callback_data="g_boy_no"),
        ],
        [
            InlineKeyboardButton("📖 توضیحات کوتاه", callback_data="info"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _main_keyboard():
    """کیبورد اصلی برای کاربر ثبت‌شده."""
    keyboard = [
        [InlineKeyboardButton("📖 توضیحات کوتاه", callback_data="info")],
        [InlineKeyboardButton("🍌 موجودی من", callback_data="my_balance")],
        [InlineKeyboardButton("🏆 برترین‌ها", callback_data="top")],
        [InlineKeyboardButton("👤 پروفایل من", callback_data="my_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- هندلر استارت (خودکار) ----------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    وقتی کاربر ربات رو استارت می‌کنه (چه با /start چه با لینک)،
    مستقیم پیام خوش‌آمد + سوال جنسیت میاد.
    """
    user = update.effective_user

    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

    safe_name = html.escape(user.first_name or "دوست")
    mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'

    # پیام اول: متن استارت
    await update.message.reply_text(
        START_TEXT.format(mention=mention),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    # پیام دوم: سوال جنسیت با ۴ دکمه + توضیحات
    await update.message.reply_text(
        GENDER_QUESTION,
        parse_mode="HTML",
        reply_markup=_gender_keyboard(),
    )


# ---------- هندلر دکمه‌ها ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # ---------- جنسیت: دختر با جنبه ----------
    if data == "g_girl_yes":
        ok = save_gender_info(user_id, "دختر", "دارم")
        if ok:
            await query.edit_message_text(
                "✅ ثبت شد!\n\n"
                "👧 <b>دختر با جنبه</b> — خوش اومدی 🎉\n"
                "می‌تونی از <b>۱۰۰٪</b> ربات استفاده کنی 😎",
                parse_mode="HTML",
                reply_markup=_main_keyboard(),
            )
        else:
            await query.edit_message_text("❌ اول ربات رو استارت کن.")

    # ---------- جنسیت: دختر بی‌جنبه ----------
    elif data == "g_girl_no":
        ok = save_gender_info(user_id, "دختر", "ندارم")
        if ok:
            await query.edit_message_text(
                "✅ ثبت شد!\n\n"
                "👧 <b>دختر بی‌جنبه</b> — خوش اومدی 🎉\n"
                "فقط از یه چیزای کمش می‌تونی استفاده کنی 😏",
                parse_mode="HTML",
                reply_markup=_main_keyboard(),
            )
        else:
            await query.edit_message_text("❌ اول ربات رو استارت کن.")

    # ---------- جنسیت: پسر با جنبه ----------
    elif data == "g_boy_yes":
        ok = save_gender_info(user_id, "پسر", "دارم")
        if ok:
            await query.edit_message_text(
                "✅ ثبت شد!\n\n"
                "👦 <b>پسر با جنبه</b> — خوش اومدی 🎉\n"
                "می‌تونی از <b>۱۰۰٪</b> ربات استفاده کنی 😎",
                parse_mode="HTML",
                reply_markup=_main_keyboard(),
            )
        else:
            await query.edit_message_text("❌ اول ربات رو استارت کن.")

    # ---------- جنسیت: پسر بی‌جنبه ----------
    elif data == "g_boy_no":
        ok = save_gender_info(user_id, "پسر", "ندارم")
        if ok:
            await query.edit_message_text(
                "✅ ثبت شد!\n\n"
                "👦 <b>پسر بی‌جنبه</b> — خوش اومدی 🎉\n"
                "فقط از یه چیزای کمش می‌تونی استفاده کنی 😏",
                parse_mode="HTML",
                reply_markup=_main_keyboard(),
            )
        else:
            await query.edit_message_text("❌ اول ربات رو استارت کن.")

    # ---------- توضیحات کوتاه ----------
    elif data == "info":
        await query.edit_message_text(
            INFO_TEXT,
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
        )

    # ---------- موجودی من ----------
    elif data == "my_balance":
        amount = get_shombool(user_id)
        await query.edit_message_text(
            f"🍌 <b>موجودی شومبول تو:</b>\n\n"
            f"📦 انبار: <b>{amount}</b> شومبول\n\n"
            f"💡 برای دریافت، توی گروه بنویس: <b>شومبول</b>",
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
        )

    # ---------- برترین‌ها ----------
    elif data == "top":
        rows = get_top_shombool(10)
        if not rows:
            await query.edit_message_text(
                "🏆 هنوز کسی شومبول جمع نکرده!",
                parse_mode="HTML",
                reply_markup=_main_keyboard(),
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 <b>برترین‌های شومبول</b>\n"]
        for i, (uid, amount, first_name) in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = html.escape(first_name or "بی‌نام")
            mention = f'<a href="tg://user?id={uid}">{name}</a>'
            lines.append(f"{medal} {mention} — <b>{amount}</b> 🍌")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
            disable_web_page_preview=True,
        )

    # ---------- پروفایل من ----------
    elif data == "my_profile":
        info = get_user_info(user_id)
        if not info:
            await query.edit_message_text("❌ اول ربات رو استارت کن.")
            return

        shombool_amount = get_shombool(user_id)
        full_name = f"{info['first_name']} {info['last_name']}".strip() or "بی‌نام"
        username = f"@{info['username']}" if info["username"] else "نداری"
        gender = info["gender"] or "ثبت نشده"
        jense = info["jense"] or "ثبت نشده"

        text = (
            f"👤 <b>پروفایل تو</b>\n\n"
            f"🆔 <code>{info['user_id']}</code>\n"
            f"📛 {html.escape(full_name)}\n"
            f"🔗 {html.escape(username)}\n"
            f"⚧ جنسیت: <b>{gender}</b>\n"
            f"🎭 جنبه: <b>{jense}</b>\n"
            f"🍌 شومبول: <b>{shombool_amount}</b>"
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=_main_keyboard(),
        )


# ---------- 🎉 خوش‌آمد گروه ----------
async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی ربات به گروه اضافه می‌شه، پیام خوش‌آمد می‌فرسته."""
    if not update.message or not update.message.new_chat_members:
        return

    bot_id = context.bot.id
    added_bot = any(member.id == bot_id for member in update.message.new_chat_members)

    if not added_bot:
        return

    chat = update.effective_chat
    logger.info(f"✅ ربات به گروه اضافه شد: {chat.title} ({chat.id})")

    try:
        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام خوش‌آمد: {e}")


# ---------- هندلر شومبول ----------
async def shombool_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id

    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

    last_claim = get_last_claim(user_id)
    now = datetime.now()

    if last_claim:
        elapsed = (now - last_claim).total_seconds()
        remaining = SHOMBOOL_COOLDOWN - elapsed

        if remaining > 0:
            remaining_int = int(remaining) + 1
            text = (
                f"⏳ <b>صبر کن کونده خان!</b> 😤\n"
                f"بعد از <b>{_format_remaining(remaining_int)}</b> "
                f"دیگه می‌تونی شومبول درخواست کنی 🍌"
            )
            await update.message.reply_text(text, parse_mode="HTML")
            return

    add_shombool(user_id, SHOMBOOL_AMOUNT)
    set_last_claim(user_id, now)

    total = get_shombool(user_id)
    safe_name = html.escape(user.first_name or "دوست")
    mention = f'<a href="tg://user?id={user_id}">{safe_name}</a>'

    text = (
        f"🍌 {mention} عزیز!\n"
        f"<b>{SHOMBOOL_AMOUNT} شومبول متوسط</b> دریافت کردی ✅\n"
        f"📦 شومبول‌های موجود در انبار: <b>{total}</b>\n\n"
        f"⏳ بعد از <b>۱ دقیقه</b> می‌تونی دوباره شومبول درخواست کنی 😉"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ---------- خطاها ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


# ---------- پاک کردن webhook ----------
async def _clear_webhook():
    async with Bot(TOKEN) as bot:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook پاک شد.")


# ---------- main ----------
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده!")

    asyncio.run(_clear_webhook())
    init_db()

    app = Application.builder().token(TOKEN).build()

    # 🎉 خوش‌آمد گروه
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler)
    )

    # 🚀 استارت (خودکار — هر پیامی که /start باشه یا اولین پیام کاربر)
    app.add_handler(
        MessageHandler(filters.Regex(r"^/start"), start_handler)
    )

    # دکمه‌های شیشه‌ای
    app.add_handler(CallbackQueryHandler(button_handler))

    # هندلر «شومبول»
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"شومبول"),
            shombool_handler,
        )
    )

    app.add_error_handler(error_handler)

    print("✅ ربات روشن شد...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
