import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from database import init_db, save_user, get_user_count, get_user_info

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

START_TEXT = """سلام {mention} 👋
شنیدم دنبال یه ربات بامزه و خودمونی می‌گردی! 🤖✨

اینجا می‌تونی شیطون باشی، بخندی و با دوستات کیف کنی 😄
یه کصخل بامزه برای گپ و گعده‌های خودمونی 🤡

🎯 امکانات:
• پاسخ‌های طنز و خودمونی
• آپدیت‌های سالیانه (قول می‌دیم!) 📅
• پشتیبانی ۲۶ ساعته (۲ ساعت اضافه‌کاری داریم) ⏰
• کاملاً رایگان، بعضی وقتا پولی 😅

شمارو بعضی وقتا به تخممون می‌گیریم 😎
عملکرد خوب که نه، ولی می‌تونی کصخل نیو داشته باشی 🍌

خوش اومدی به جمع ما 💛
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 💾 ذخیره اطلاعات کاربر در دیتابیس
    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or ""
    )

    mention = f"[{user.first_name}](tg://user?id={user.id})"
    await update.message.reply_text(
        START_TEXT.format(mention=mention),
        parse_mode="Markdown"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /stats برای دیدن تعداد کاربران"""
    count = get_user_count()
    await update.message.reply_text(
        f"👥 تعداد کاربران: **{count}**",
        parse_mode="Markdown"
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /me برای دیدن اطلاعات ذخیره‌شده کاربر"""
    user = update.effective_user
    info = get_user_info(user.id)

    if not info:
        await update.message.reply_text("❌ اطلاعاتی ازت پیدا نشد. اول /start بزن.")
        return

    text = (
        f"🆔 آیدی: `{info['user_id']}`\n"
        f"👤 اسم: {info['first_name']} {info['last_name']}\n"
        f"📛 یوزرنیم: @{info['username'] or 'نداری'}\n"
        f"📅 تاریخ عضویت: {info['created_at'][:10]}\n"
        f"⏰ آخرین بازدید: {info['last_seen'][:10]}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN تو فایل .env تنظیم نشده!")

    # 🔧 ساخت جدول دیتابیس در شروع
    init_db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("me", me))
    print("✅ ربات روشن شد...")
    app.run_polling()


if __name__ == "__main__":
    main()
