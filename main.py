import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from handlers import start_handler, text_handler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("shomped")


async def on_startup(app: Application) -> None:
    await init_db()
    logger.info("✅ دیتابیس آماده است.")


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # فقط /start با اسلش می‌مونه (چون تلگرام اجبار داره)
    app.add_handler(CommandHandler("start", start_handler))

    # همه‌ی پیام‌های متنی (راهنما، پروفایل، برترها، کلمات کلیدی)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    return app


def run() -> None:
    app = build_application()
    logger.info("🤖 ربات شومپد در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()
