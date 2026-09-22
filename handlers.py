import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from keyboards import start_keyboard
from messages import HELP_TEXT, START_TEXT
from repository import get_or_create_user

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return

    try:
        await get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
    except Exception as exc:
        logger.exception("DB error: %s", exc)

    await update.message.reply_text(
        START_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)
