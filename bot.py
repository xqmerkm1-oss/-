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
    my_points, my_points_handler,
    group_welcome, rahnama_handler, help_callback, points_handler,
    auto_close_help_panel,
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

    # ===== دستورات اسلش =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mypoints", my_points))
    app.add_handler(CommandHandler("stats", stats))

    # ===== کیبوردها =====
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))
    app.add_handler(CallbackQueryHandler(
        confirm_choice, pattern="^(confirm|cancel)_"
    ))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))

    # ===== گروه =====
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        group_welcome,
    ))

    # راهنما (کلمه «راهنما»)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex("راهنما"),
        rahnama_handler,
    ))

    # ===== کلمات پوینت (فقط تک‌کلمه‌ای) =====
    single_words_pattern = (
        r"^\s*("
        + KIR_WORD + "|"
        + KOS_WORD + "|"
        + MALE_GOOD_WORD + "|"
        + FEMALE_GOOD_WORD + "|"
        + HIGH_WORD + "|"
        + TOP_WORD
        + r")\s*$"
    )

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(single_words_pattern),
        points_handler,
    ))

    # ===== دستورات نمایش پوینت (کیرام / کصام / پوینتام) =====
    my_points_pattern = (
        r"^\s*(کیرام|کیرهام|کیر هام|کیرها|"
        r"کصام|کصهام|کص هام|کصها|"
        r"پوینتام|پوینتهام|پوینت هام|پوینتها)\s*$"
    )

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(my_points_pattern),
        my_points_handler,
    ))

    # ===== تایمر بستن خودکار پنل راهنما =====
    if app.job_queue:
        app.job_queue.run_repeating(
            auto_close_help_panel,
            interval=30,
            first=30,
            name="auto_close_help",
        )
        logger.info("✅ Help auto-close timer started (every 30s)")

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
