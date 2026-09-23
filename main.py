import asyncio
import logging

from alembic import command
from alembic.config import Config
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from handlers import (
    check_membership_callback,
    menu_callback,
    start_handler,
    text_handler,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("shomped")


def run_migrations():
    """Alembic migration رو اجرا می‌کنه."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ دیتابیس migrate شد.")
    except Exception as exc:
        logger.exception("Alembic error: %s", exc)


async def on_startup(app: Application) -> None:
    # migration توی thread جداگانه (چون sync هست)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_migrations)
    logger.info("✅ دیتابیس آماده است.")


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(
        CallbackQueryHandler(check_membership_callback, pattern="^check_membership$")
    )
    app.add_handler(
        CallbackQueryHandler(menu_callback, pattern="^menu_")
    )
    app.add_handler(CommandHandler("start", start_handler))
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
