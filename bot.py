import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ChatMemberHandler,
)

from config import BOT_TOKEN, KIR_WORD
from database import init_db
from handlers import (
    start, check_join, gender_choice, confirm_choice, stats,
    welcome_to_group, kir_handler,
)

# ===== لاگ =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
PORT = int(os.getenv("PORT", "8080"))


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # ===== هندلرهای خصوصی =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))
    app.add_handler(CallbackQueryHandler(
        confirm_choice, pattern="^(confirm|cancel)_"
    ))

    # ===== هندلرهای گروه =====
    # خوشامد ربات وقتی به گروه اضافه میشه
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome_to_group,
    ))

    # کیر پوینت — وقتی کسی «کیر» نوشت
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"کیر"),
        kir_handler,
    ))

    if RAILWAY_DOMAIN:
        webhook_url = f"https://{RAILWAY_DOMAIN}/{BOT_TOKEN}"
        logger.info(f"✅ Starting webhook on {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        logger.info("✅ Starting polling (local mode)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
