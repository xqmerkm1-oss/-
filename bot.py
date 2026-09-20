import os
import html
import asyncio
import logging
from datetime import datetime

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import (
    init_db,
    save_user,
    save_gender_info,
    get_user_info,
    get_shombool,
    add_shombool,
    reset_shombool,
    get_chochol,
    add_chochol,
    reset_chochol,
    get_last_shombool_claim,
    set_last_shombool_claim,
    get_last_chochol_claim,
    set_last_chochol_claim,
    get_warning_count,
    add_warning,
    reset_warnings,
    get_top_shombool,
    get_top_chochol,
)

# ---------- لاگ ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

SHOMBOOL_AMOUNT = 5
CHOCHOL_AMOUNT = 5
COOLDOWN = 180
MAX_WARNINGS = 3
SELF_BOT_WINDOW = 5
SELF_BOT_THRESHOLD = 3

# 🎉 متن خوش‌آمد گروه
WELCOME_TEXT = """🎉 <b>یه جقی وارد گروه شده</b> 🍌
پاشید <b>جق بزنید</b> 💦✊

━━━━━━━━━━━━━━━
🍌 برای دریافت شومبول بنویسید: <b>شومبول</b>"""

# 📝 سوال جنسیت (هم برای استارت، هم برای گروه)
GENDER_QUESTION = """🎭 <b>جنسیتت چیه؟</b>

⚠️ <b>فقط یه بار</b> می‌تونی انتخاب کنی!"""

# ---------- ۴ متن خوش‌آمد (طبق پیامت) ----------

# 👧 دخترم، جنبه ندارم → «سلام خانوم محترم»
WELCOME_GIRL_NO = """🌸 <b>سلام خانوم محترم</b> 🌸
خوش اومدی به ربات ما 💖
امیدوارم که بمونی با قلب سفید، شایدم قرمز ❤️🤍

✨ <b>خوبی این ربات اینکه</b> می‌تونی وجود خودتو به بقیه اثبات کنی 💫
کلاً ربات خوبیه، هرکی استفاده کرده راضی بود 😍
مخصوصاً اونایی که استارت کردن رباتو 🚀"""

# 👧 دخترم، جنبه دارم → «سلام شنیدم که می‌خوای کصخل باشی»
WELCOME_GIRL_YES = """😏 <b>سلام شنیدم که می‌خوای کصخل باشی</b> 🤡

تو می‌تونی یه <b>کصخل گوگولی</b> باشی که خیلیا تو رو دوست خواهند داشت 🥰
مخصوصاً اگه <b>ایرانی</b> باشن 🇮🇷

🍌 <b>شومبول</b> و <b>نازسرین</b> جمع کن تا بتونی کصخل بهتری باشی 🚀"""

# 👦 پسرم، جنبه ندارم → «سلام آقای خوشتیپ»
WELCOME_BOY_NO = """😎 <b>سلام آقای خوشتیپ</b> 😎
خوش اومدی به ربات ما 🎉
امیدوارم که اینجا بهت خوش بگذره 🥳

✨ <b>خوبی ربات ما اینکه</b> می‌تونی ربات خودتو بنا به خواسته‌هات شخصی‌سازی کنی 🎨
(به صورت محدود 😅)
و جملات خوبی می‌تونی برای <b>افزایش اعتبار</b> استفاده کنی 📈

همین دیگه، مونده <b>گار باشی</b> 💪
فعلاً 👋"""

# 👦 پسرم، جنبه دارم → «شنیدم دلت شومبول می‌خواد»
WELCOME_BOY_YES = """🍌 <b>شنیدم دلت شومبول می‌خواد</b> 🍌
تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به‌گایی‌هات برای ایران 🤡

🎯 <b>شوبول</b> و <b>نازسرین</b> جمع کن تا بتونی کصخل بهتری باشی

━━━━━━━━━━━━━━━
😎 شمارو بعضی وقتا به تخممون می‌گیریم
📈 عملکرد خوب که نه، ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی
🔄 <b>آپدیت‌های سالیانه</b> میدیم بیرون
🤝 مثل شما می‌تونیم یه کصخل باشیم
🕐 پشتیبانی <b>۲۶ ساعته</b>
💰 کاملاً <b>رایگان</b> — بعضی وقتا پولی 😏"""


# ---------- کمکی ----------
def _format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "الان"
    m, s = divmod(seconds, 60)
    if m and s:
        return f"<b>{m}</b> دقیقه و <b>{s}</b> ثانیه"
    elif m:
        return f"<b>{m}</b> دقیقه"
    else:
        return f"<b>{s}</b> ثانیه"


def _gender_keyboard():
    """دکمه‌های جنسیت (هم برای استارت، هم برای گروه)."""
    keyboard = [
        [
            InlineKeyboardButton("👧 دخترم، جنبه ندارم", callback_data="g_girl_no"),
            InlineKeyboardButton("👧 دخترم، جنبه دارم", callback_data="g_girl_yes"),
        ],
        [
            InlineKeyboardButton("👦 پسرم، جنبه ندارم", callback_data="g_boy_no"),
            InlineKeyboardButton("👦 پسرم، جنبه دارم", callback_data="g_boy_yes"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- ضد سلف ----------
async def _check_self_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    now = datetime.now()

    key = "self_bot_times"
    if key not in context.user_data:
        context.user_data[key] = []

    times = context.user_data[key]
    times = [t for t in times if (now - t).total_seconds() < SELF_BOT_WINDOW]
    times.append(now)
    context.user_data[key] = times

    if len(times) > SELF_BOT_THRESHOLD:
        context.user_data[key] = []
        warning_count = add_warning(user_id)

        if warning_count >= MAX_WARNINGS:
            reset_shombool(user_id)
            reset_chochol(user_id)
            reset_warnings(user_id)
            await update.message.reply_text(
                "🚫 <b>سلف‌بات شناسایی شد!</b>\n\n"
                "❌ <b>۳ بار اخطار گرفتی</b>\n"
                "💀 <b>همه‌ی شومبول‌ها و چوچول‌هات صفر شد!</b>\n\n"
                "⚠️ اگه بازم ادامه بدی، محدودتر می‌شی.",
                parse_mode="HTML",
            )
        else:
            remaining = MAX_WARNINGS - warning_count
            await update.message.reply_text(
                f"⚠️ <b>اخطار سلف‌بات!</b> ({warning_count}/{MAX_WARNINGS})\n\n"
                f"🤖 رفتار ربات‌مانند شناسایی شد\n"
                f"⏳ <b>{remaining} اخطار دیگه</b> تا صفر شدن ارزت مونده\n\n"
                f"💡 اگه واقعاً خودتی، یه کم صبر کن و دوباره امتحان کن.",
                parse_mode="HTML",
            )
        return True

    return False


# ---------- هندلر استارت ----------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
    )
    context.user_data.pop("self_bot_times", None)

    # چک کن قبلاً جنسیت ثبت کرده یا نه
    info = get_user_info(user.id)
    if info and info.get("gender"):
        # قبلاً ثبت کرده — فقط پیام خوش‌آمد
        await update.message.reply_text(
            f"✅ قبلاً ثبت کردی!\n\n"
            f"⚧ جنسیت: <b>{info['gender']}</b>\n"
            f"🎭 جنبه: <b>{info['jense'] or 'ندارم'}</b>",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        GENDER_QUESTION,
        parse_mode="HTML",
        reply_markup=_gender_keyboard(),
    )


# ---------- هندلر دکمه‌ها ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # ذخیره‌ی اطلاعات کاربر (اگه جدید باشه)
    save_user(
        user_id=query.from_user.id,
        first_name=query.from_user.first_name or "",
        last_name=query.from_user.last_name or "",
        username=query.from_user.username or "",
    )

    # «دخترم، جنبه ندارم»
    if data == "g_girl_no":
        ok = save_gender_info(user_id, "دختر", "ندارم")
        if ok:
            await query.edit_message_text(WELCOME_GIRL_NO, parse_mode="HTML")
        else:
            await query.edit_message_text(
                "⚠️ <b>قبلاً انتخاب کردی!</b>\n"
                "❌ نمی‌تونی دوباره عوض کنی.",
                parse_mode="HTML",
            )

    # «دخترم، جنبه دارم»
    elif data == "g_girl_yes":
        ok = save_gender_info(user_id, "دختر", "دارم")
        if ok:
            await query.edit_message_text(WELCOME_GIRL_YES, parse_mode="HTML")
        else:
            await query.edit_message_text(
                "⚠️ <b>قبلاً انتخاب کردی!</b>\n"
                "❌ نمی‌تونی دوباره عوض کنی.",
                parse_mode="HTML",
            )

    # «پسرم، جنبه ندارم»
    elif data == "g_boy_no":
        ok = save_gender_info(user_id, "پسر", "ندارم")
        if ok:
            await query.edit_message_text(WELCOME_BOY_NO, parse_mode="HTML")
        else:
            await query.edit_message_text(
                "⚠️ <b>قبلاً انتخاب کردی!</b>\n"
                "❌ نمی‌تونی دوباره عوض کنی.",
                parse_mode="HTML",
            )

    # «پسرم، جنبه دارم»
    elif data == "g_boy_yes":
        ok = save_gender_info(user_id, "پسر", "دارم")
        if ok:
            await query.edit_message_text(WELCOME_BOY_YES, parse_mode="HTML")
        else:
            await query.edit_message_text(
                "⚠️ <b>قبلاً انتخاب کردی!</b>\n"
                "❌ نمی‌تونی دوباره عوض کنی.",
                parse_mode="HTML",
            )


# ---------- 🎉 خوش‌آمد گروه ----------
async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    bot_id = context.bot.id
    added_bot = any(member.id == bot_id for member in update.message.new_chat_members)

    if not added_bot:
        return

    try:
        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام خوش‌آمد: {e}")


# ---------- ✅ هندلر شومبول (فقط پسر با جنبه) ----------
async def shombool_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id

    message_text = (update.message.text or "").strip()
    cleaned = message_text.replace("🍌", "").strip()

    if cleaned != "شومبول":
        return

    # اگه کاربر ثبت‌نام نکرده → دکمه‌های جنسیت
    info = get_user_info(user_id)
    if not info or not info.get("gender"):
        save_user(
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            username=user.username or "",
        )
        await update.message.reply_text(
            "🎭 <b>اول جنسیتت رو انتخاب کن!</b>\n\n"
            "⚠️ <b>فقط یه بار</b> می‌تونی انتخاب کنی!",
            parse_mode="HTML",
            reply_markup=_gender_keyboard(),
        )
        return

    if await _check_self_bot(update, context):
        return

    gender = info.get("gender")
    jense = info.get("jense")

    # فقط پسر با جنبه
    if not (gender == "پسر" and jense == "دارم"):
        if gender == "دختر":
            await update.message.reply_text(
                "❌ <b>دخترا نمی‌تونن شومبول بزنن!</b>\n"
                "🍆 برو <b>چوچول</b> بزن 😏",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "❌ <b>تو نمی‌تونی شومبول بزنی!</b>\n"
                "فقط <b>پسرای با جنبه</b> می‌تونن 😎",
                parse_mode="HTML",
            )
        return

    last_claim = get_last_shombool_claim(user_id)
    now = datetime.now()

    if last_claim:
        elapsed = (now - last_claim).total_seconds()
        remaining = COOLDOWN - elapsed
        if remaining > 0:
            remaining_int = int(remaining) + 1
            await update.message.reply_text(
                f"⏳ <b>صبر کن کونده خان!</b> 😤\n"
                f"بعد از <b>{_format_remaining(remaining_int)}</b> "
                f"دیگه می‌تونی شومبول درخواست کنی 🍌",
                parse_mode="HTML",
            )
            return

    add_shombool(user_id, SHOMBOOL_AMOUNT)
    set_last_shombool_claim(user_id, now)

    total = get_shombool(user_id)
    safe_name = html.escape(user.first_name or "دوست")
    mention = f'<a href="tg://user?id={user_id}">{safe_name}</a>'

    await update.message.reply_text(
        f"🍌 {mention} عزیز!\n"
        f"<b>{SHOMBOOL_AMOUNT} شومبول</b> دریافت کردی ✅\n"
        f"📦 شومبول‌های موجود در انبار: <b>{total}</b>\n\n"
        f"⏳ بعد از <b>۳ دقیقه</b> می‌تونی دوباره شومبول درخواست کنی 😉",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ---------- ✅ هندلر چوچول (فقط دختر با جنبه) ----------
async def chochol_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id

    message_text = (update.message.text or "").strip()
    cleaned = message_text.replace("🍆", "").strip()

    if cleaned != "چوچول":
        return

    # اگه کاربر ثبت‌نام نکرده → دکمه‌های جنسیت
    info = get_user_info(user_id)
    if not info or not info.get("gender"):
        save_user(
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            username=user.username or "",
        )
        await update.message.reply_text(
            "🎭 <b>اول جنسیتت رو انتخاب کن!</b>\n\n"
            "⚠️ <b>فقط یه بار</b> می‌تونی انتخاب کنی!",
            parse_mode="HTML",
            reply_markup=_gender_keyboard(),
        )
        return

    if await _check_self_bot(update, context):
        return

    gender = info.get("gender")
    jense = info.get("jense")

    # فقط دختر با جنبه
    if not (gender == "دختر" and jense == "دارم"):
        if gender == "پسر":
            await update.message.reply_text(
                "❌ <b>پسرا نمی‌تونن چوچول بزنن!</b>\n"
                "🍌 برو <b>شومبول</b> بزن 😏",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "❌ <b>تو نمی‌تونی چوچول بزنی!</b>\n"
                "فقط <b>دخترای با جنبه</b> می‌تونن 😎",
                parse_mode="HTML",
            )
        return

    last_claim = get_last_chochol_claim(user_id)
    now = datetime.now()

    if last_claim:
        elapsed = (now - last_claim).total_seconds()
        remaining = COOLDOWN - elapsed
        if remaining > 0:
            remaining_int = int(remaining) + 1
            await update.message.reply_text(
                f"⏳ <b>صبر کن کونده خان!</b> 😤\n"
                f"بعد از <b>{_format_remaining(remaining_int)}</b> "
                f"دیگه می‌تونی چوچول درخواست کنی 🍆",
                parse_mode="HTML",
            )
            return

    add_chochol(user_id, CHOCHOL_AMOUNT)
    set_last_chochol_claim(user_id, now)

    total = get_chochol(user_id)
    safe_name = html.escape(user.first_name or "دوست")
    mention = f'<a href="tg://user?id={user_id}">{safe_name}</a>'

    await update.message.reply_text(
        f"🍆 {mention} عزیز!\n"
        f"<b>{CHOCHOL_AMOUNT} چوچول</b> دریافت کردی ✅\n"
        f"📦 چوچول‌های موجود در انبار: <b>{total}</b>\n\n"
        f"⏳ بعد از <b>۳ دقیقه</b> می‌تونی دوباره چوچول درخواست کنی 😉",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ---------- خطاها ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


# ---------- پاک کردن webhook ----------
async def _clear_webhook():
    async with Bot(TOKEN) as bot:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook پاک شد.")


# ---------- main ----------
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده!")

    asyncio.run(_clear_webhook())
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler)
    )

    app.add_handler(
        MessageHandler(filters.Regex(r"^/start"), start_handler)
    )

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            shombool_handler,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chochol_handler,
        )
    )

    app.add_error_handler(error_handler)

    print("✅ ربات روشن شد...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
