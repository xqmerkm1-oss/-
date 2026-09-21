import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
)

from config import BOT_TOKEN
from database import init_db
from handlers import start, check_join, gender_choice, stats

# ===== لاگ برای دیباگ =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Railway این متغیر رو خودکار ست میکنه
RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
PORT = int(os.getenv("PORT", "8080"))


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))

    if RAILWAY_DOMAIN:
        # ===== حالت Webhook (روی Railway) =====
        webhook_url = f"https://{RAILWAY_DOMAIN}/{BOT_TOKEN}"
        logger.info(f"✅ Starting webhook on {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        # ===== حالت Polling (لوکال) =====
        logger.info("✅ Starting polling (local mode)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
