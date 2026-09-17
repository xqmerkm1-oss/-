import os
import html
import asyncio
import logging

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from database import (
    init_db,
    save_user,
    save_gender,
    get_user_count,
    get_user_info,
)

# ---------- تنظیمات ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

START_TEXT = os.getenv(
    "START_TEXT",
    """سلام {mention} 👋
شنیدم دلت <b>شومبول</b> می‌خواد 🍌
تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به‌گایی‌هات برای ایران 🤡

🎯 <b>شوبول</b> و <b>نازسرین</b> جمع کن تا بتونی کصخل بهتری باشی

━━━━━━━━━━━━━━━
😎 شمارو بعضی وقتا به تخممون می‌گیریم
📈 عملکرد خوب که نه، ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی
🔄 <b>آپدیت‌های سالیانه</b> میدیم بیرون
🤝 مثل شما می‌تونیم یه کصخل باشیم
🕐 پشتیبانی <b>۲۶ ساعته</b>
💰 کاملاً <b>رایگان</b> — بعضی وقتا پولی 😏"""
)


# ---------- هندلرها ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

    # escape کردن نام برای جلوگیری از خطای HTML
    safe_name = html.escape(user.first_name or "دوست")
    mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'

    keyboard = [
        [InlineKeyboardButton("🚀 شروع به کار", callback_data="start_work")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        START_TEXT.format(mention=mention),
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_work":
        keyboard = [
            [InlineKeyboardButton("👧 من دخترم", callback_data="gender_girl")],
            [InlineKeyboardButton("👦 من پسرم", callback_data="gender_boy")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "جنسیتت چیه؟ 🤔",
            reply_markup=reply_markup,
        )

    elif query.data == "gender_girl":
        ok = save_gender(query.from_user.id, "دختر")
        if ok:
            await query.edit_message_text("ثبت شد ✅\nخوش اومدی 👧")
        else:
            await query.edit_message_text("❌ اول /start بزن.")

    elif query.data == "gender_boy":
        ok = save_gender(query.from_user.id, "پسر")
        if ok:
            await query.edit_message_text("ثبت شد ✅\nخوش اومدی 👦")
        else:
            await query.edit_message_text("❌ اول /start بزن.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_user_count()
    await update.message.reply_text(f"👥 کاربران: <b>{count}</b>", parse_mode="HTML")


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info = get_user_info(user.id)

    if not info:
        await update.message.reply_text("❌ اول /start بزن.")
        return

    full_name = f"{info['first_name']} {info['last_name']}".strip() or "بی‌نام"
    username = f"@{info['username']}" if info["username"] else "نداری"
    gender = info["gender"] or "ثبت نشده"

    text = (
        f"🆔 <code>{info['user_id']}</code>\n"
        f"👤 {html.escape(full_name)}\n"
        f"📛 {html.escape(username)}\n"
        f"⚧ جنسیت: {gender}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ---------- خطاها ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


# ---------- پاک کردن webhook قبل از polling ----------
async def _clear_webhook():
    """حذف webhook و پیام‌های معلق، برای جلوگیری از خطای 409 Conflict."""
    async with Bot(TOKEN) as bot:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook پاک شد.")


# ---------- main ----------
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده!")

    # پاک کردن webhook قبل از شروع polling
    asyncio.run(_clear_webhook())

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print("✅ ربات روشن شد...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
