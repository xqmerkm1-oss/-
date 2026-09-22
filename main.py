import logging

from telegram import Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from handlers import help_handler, keyword_reward_handler, start_handler

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
        .rate_limiter(AIORateLimiter(max_rate=25, time_period=1.0))
        .post_init(on_startup)
        .build()
    )

    # دستورات
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # هندلر کلمات کلیدی — باید آخر اضافه بشه
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_reward_handler)
    )

    return app


def run() -> None:
    app = build_application()
    logger.info("🤖 ربات شومپد در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()
