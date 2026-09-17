import os
import html
import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import (
    init_db,
    save_user,
    save_gender,
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
SHOMBOOL_AMOUNT = 20          # مقدار هر دریافت
SHOMBOOL_COOLDOWN = 60        # ثانیه

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


# ---------- کمکی: نمایش ثانیه به فرمت خوانا ----------
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


# ---------- هندلرها ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

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


# ---------- هندلر اصلی: شنیدن «شومبول» ----------
async def shombool_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    وقتی کاربر توی گروه یا چت خصوصی می‌نویسه «شومبول»،
    ۲۰ شومبول متوسط بهش داده می‌شه.
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id

    # اطمینان از اینکه کاربر توی دیتابیس هست
    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )

    # چک کردن cooldown
    last_claim = get_last_claim(user_id)
    now = datetime.now()

    if last_claim:
        elapsed = (now - last_claim).total_seconds()
        remaining = SHOMBOOL_COOLDOWN - elapsed

        if remaining > 0:
            # هنوز تو cooldown هست
            remaining_int = int(remaining) + 1  # رند به بالا
            text = (
                f"⏳ <b>صبر کن بابا!</b> 😤\n"
                f"بعد از <b>{_format_remaining(remaining_int)}</b> "
                f"دیگه می‌تونی شومبول درخواست کنی 🍌"
            )
            await update.message.reply_text(text, parse_mode="HTML")
            return

    # ---- دادن شومبول ----
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


# ---------- دستورات ----------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_user_count()
    await update.message.reply_text(
        f"👥 کاربران: <b>{count}</b>",
        parse_mode="HTML",
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info = get_user_info(user.id)

    if not info:
        await update.message.reply_text("❌ اول /start بزن.")
        return

    shombool_amount = get_shombool(user.id)

    full_name = f"{info['first_name']} {info['last_name']}".strip() or "بی‌نام"
    username = f"@{info['username']}" if info["username"] else "نداری"
    gender = info["gender"] or "ثبت نشده"

    text = (
        f"🆔 <code>{info['user_id']}</code>\n"
        f"👤 {html.escape(full_name)}\n"
        f"📛 {html.escape(username)}\n"
        f"⚧ جنسیت: {gender}\n"
        f"🍌 شومبول: <b>{shombool_amount}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def shombool_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shombool — نمایش موجودی شومبول."""
    user = update.effective_user
    amount = get_shombool(user.id)
    await update.message.reply_text(
        f"🍌 شومبول‌های موجود در انبار تو: <b>{amount}</b>",
        parse_mode="HTML",
    )


async def top_shombool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏆 برترین‌های شومبول."""
    rows = get_top_shombool(10)

    if not rows:
        await update.message.reply_text(
            "🏆 هنوز کسی شومبول جمع نکرده!",
            parse_mode="HTML",
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>برترین‌های شومبول</b>\n"]

    for i, (user_id, amount, first_name) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = html.escape(first_name or "بی‌نام")
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'
        lines.append(f"{medal} {mention} — <b>{amount}</b> 🍌")

    await update.message.reply_text(
        "\n".join(lines),
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

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("shombool", shombool_balance))
    app.add_handler(CommandHandler("top", top_shombool))

    # دکمه‌های شیشه‌ای
    app.add_handler(CallbackQueryHandler(button_handler))

    # ✅ هندلر «شومبول» — توی گروه و چت خصوصی
    #    فقط پیام‌های متنی که کلمه‌ی «شومبول» توشون هست
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
