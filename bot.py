import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)

from config import (
    BOT_TOKEN,
    KIR_WORD, KOS_WORD, MALE_GOOD_WORD, FEMALE_GOOD_WORD,
    HIGH_WORD, TOP_WORD,
)
from database import init_db
from handlers import (
    start, check_join, gender_choice, confirm_choice, stats,
    help_command, my_points,
    group_welcome, points_handler,
)

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

    # ===== چت خصوصی =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mypoints", my_points))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))
    app.add_handler(CallbackQueryHandler(
        confirm_choice, pattern="^(confirm|cancel)_"
    ))

    # ===== گروه =====
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        group_welcome,
    ))

    # ===== کلمات کلیدی (همه توی یه هندلر) =====
    all_words_pattern = "|".join([
        KIR_WORD, KOS_WORD,
        MALE_GOOD_WORD, FEMALE_GOOD_WORD,
        HIGH_WORD, TOP_WORD,
    ])

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(all_words_pattern),
        points_handler,
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
