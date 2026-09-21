from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
)

from config import BOT_TOKEN
from database import init_db
from handlers import start, check_join, gender_choice, stats


def main():
    # ساخت جدول‌های دیتابیس
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))

    print("✅ ربات روشن شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
