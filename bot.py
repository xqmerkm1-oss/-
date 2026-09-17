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

SHOMBOOL_AMOUNT = 5
SHOMBOOL_COOLDOWN = 60

# 🎉 متن خوش‌آمد گروه
WELCOME_TEXT = """🎉 <b>یه جقی وارد گروه شده</b> 🍌
پاشید <b>جق بزنید</b> 💦✊

━━━━━━━━━━━━━━━
🍌 برای دریافت شومبول بنویسید: <b>شومبول</b>"""

# 📝 سوال جنسیت (فقط همین، بدون توضیح اضافه)
GENDER_QUESTION = "🎭 <b>جنسیتت چیه؟</b>"

# ---------- ۴ متن خوش‌آمد ----------

# 👧 دختر با جنبه
WELCOME_GIRL_YES = """🌸 <b>سلام خانوم محترم</b> 🌸
خوش اومدی به ربات ما 💖
امیدوارم که بمونی با قلب سفید، شایدم قرمز ❤️🤍

✨ <b>خوبی این ربات اینکه</b> می‌تونی وجود خودتو به بقیه اثبات کنی 💫
کلاً ربات خوبیه، هرکی استفاده کرده راضی بود 😍
مخصوصاً اونایی که استارت کردن رباتو 🚀"""

# 👧 دختر بی‌جنبه
WELCOME_GIRL_NO = """😏 <b>سلام شنیدم که می‌خوای کصخل باشی</b> 🤡

تو می‌تونی یه <b>کصخل گوگولی</b> باشی که خیلیا تو رو دوست خواهند داشت 🥰
مخصوصاً اگه <b>ایرانی</b> باشن 🇮🇷

🍌 <b>شومبول</b> و <b>نازسرین</b> جمع کن تا بتونی کصخل بهتری باشی"""

# 👦 پسر با جنبه
WELCOME_BOY_YES = """😎 <b>سلام آقای خوشتیپ</b> 😎
خوش اومدی به ربات ما 🎉
امیدوارم که اینجا بهت خوش بگذره 🥳

✨ <b>خوبی ربات ما اینکه</b> می‌تونی ربات خودتو بنا به خواسته‌هات شخصی‌سازی کنی 🎨
(به صورت محدود 😅)
و جملات خوبی می‌تونی برای <b>افزایش اعتبار</b> استفاده کنی 📈

همین دیگه، مونده <b>گار باشی</b> 💪
فعلاً 👋"""

# 👦 پسر بی‌جنبه
WELCOME_BOY_NO = """🍌 <b>شنیدم دلت شومبول می‌خواد</b> 🍌
تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به‌گایی‌هات برای ایران 🤡

🎯 <b>شوبول</b> و <b>نازسرین</b> جمع کن تا بتونی کصخل بهتری باشی

━━━━━━━━━━━━━━━
😎 شمارو بعضی وقتا به تخممون می‌گیریم
📈 عملکرد خوب که نه، ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی
🔄 <b>آپدیت‌های سالیانه</b> میدیم بیرون
🤝 مثل شما می‌تونیم یه کصخل باشیم
🕐 پشتیبانی <b>۲۶ ساعته</b>
💰 کاملاً <b>رایگان</b> — بعضی وقتا پولی 😏"""


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
    keyboard = [
        [
            InlineKeyboardButton("👧 دخترم، جنبه دارم", callback_data="g_girl_yes"),
            InlineKeyboardButton("👧 دخترم، جنبه ندارم", callback_data="g_girl_no"),
        ],
        [
            InlineKeyboardButton("👦 پسرم، جنبه دارم", callback_data="g_boy_yes"),
            InlineKeyboardButton("👦 پسرم، جنبه ندارم", callback_data="g_boy_no"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- هندلر استارت ----------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

    # فقط سوال جنسیت + دکمه‌ها
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

    if data == "g_girl_yes":
        ok = save_gender_info(user_id, "دختر", "دارم")
        if ok:
            await query.edit_message_text(WELCOME_GIRL_YES, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ اول /start بزن.")

    elif data == "g_girl_no":
        ok = save_gender_info(user_id, "دختر", "ندارم")
        if ok:
            await query.edit_message_text(WELCOME_GIRL_NO, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ اول /start بزن.")

    elif data == "g_boy_yes":
        ok = save_gender_info(user_id, "پسر", "دارم")
        if ok:
            await query.edit_message_text(WELCOME_BOY_YES, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ اول /start بزن.")

    elif data == "g_boy_no":
        ok = save_gender_info(user_id, "پسر", "ندارم")
        if ok:
            await query.edit_message_text(WELCOME_BOY_NO, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ اول /start بزن.")


# ---------- 🎉 خوش‌آمد گروه ----------
async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


# ---------- ✅ هندلر شومبول ----------
async def shombool_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id

    message_text = (update.message.text or "").strip()
    cleaned = message_text.replace("🍌", "").strip()

    if cleaned != "شومبول":
        return

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

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler)
    )

    app.add_handler(
        MessageHandler(filters.Regex(r"^/start"), start_handler)
    )

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
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
