from telegram import Update
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from database import (
    create_or_update_user, set_user_joined, set_user_gender,
    log_join_action, get_user, get_stats,
)
from keyboards import join_keyboard, gender_keyboard


# ====== متنها ======
WELCOME_TEXT = (
    "به ربات کصخل خیز خوش اومدین برای استفاده از ربات ابتدا باید "
    "عضو کانال کصخل خیز درجه یک شوید !\n"
    "لینک کانال\n"
    "https://t.me/Afirstratescumbag\n"
    "ایدی عددی کانال\n"
    f"{CHANNEL_ID}"
)

NOT_JOINED_TEXT = (
    "جقی هنوز عضو نشدی داری عضو شدمو میزنی عضو کانال شو ببینم تا نکردمت عه کصکش !"
)

JOINED_TEXT = (
    "بلخره عضو شدی آفرین از جقی بودن دراومدی حالا جنسیتت رو از دکمه های زیر انتخاب کن !"
)


async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """چک میکنه کاربر عضو کانال هست یا نه"""
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID, user_id=user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"[is_member error] {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start - پیام خوشامد"""
    user = update.effective_user

    # ذخیره کاربر در دیتابیس
    create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    joined = await is_member(context, user.id)
    set_user_joined(user.id, joined)
    log_join_action(user.id, "start")

    if joined:
        db_user = get_user(user.id)
        # اگه قبلاً جنسیت انتخاب کرده
        if db_user and db_user.get("gender"):
            await update.message.reply_text(
                f"خوش برگشتی {user.first_name} 👋\n"
                f"جنسیتت: {'پسر 👦' if db_user['gender'] == 'male' else 'دختر 👧'}"
            )
            return
        await update.message.reply_text(
            JOINED_TEXT,
            reply_markup=gender_keyboard(),
        )
    else:
        await update.message.reply_text(
            WELCOME_TEXT,
            reply_markup=join_keyboard(),
        )


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کلیک روی دکمه «عضو شدم»"""
    query = update.callback_query
    user_id = query.from_user.id
    joined = await is_member(context, user_id)

    set_user_joined(user_id, joined)
    log_join_action(user_id, "check_join")

    if not joined:
        try:
            await query.edit_message_text(
                NOT_JOINED_TEXT,
                reply_markup=join_keyboard(),
            )
        except Exception:
            await query.message.reply_text(
                NOT_JOINED_TEXT,
                reply_markup=join_keyboard(),
            )
        await query.answer("هنوز عضو نشدی!", show_alert=True)
        return

    # عضو شده → پیام قبلی رو پاک کن
    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=JOINED_TEXT,
        reply_markup=gender_keyboard(),
    )
    await query.answer("عضو شدی ✅")


async def gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب جنسیت"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "gender_male":
        gender, label = "male", "پسر 👦"
    elif data == "gender_female":
        gender, label = "female", "دختر 👧"
    else:
        await query.answer()
        return

    set_user_gender(user_id, gender)

    try:
        await query.edit_message_text(
            f"جنسیتت ثبت شد: {label}\nحالا میتونی از ربات استفاده کنی."
        )
    except Exception:
        pass
    await query.answer(f"ثبت شد: {label}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats - آمار (فقط برای ادمین)"""
    s = get_stats()
    text = (
        "📊 آمار ربات\n\n"
        f"👥 کل کاربران: {s['total']}\n"
        f"✅ عضو کانال: {s['joined']}\n"
        f"👦 پسر: {s['males']}\n"
        f"👧 دختر: {s['females']}"
    )
    await update.message.reply_text(text)
