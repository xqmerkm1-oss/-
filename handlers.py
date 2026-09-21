from telegram import Update
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from database import (
    create_or_update_user, set_user_joined, set_user_gender,
    log_join_action, get_user, get_stats,
)
from keyboards import join_keyboard, gender_keyboard


# ===== متنها (بولد + ایموجی) =====
WELCOME_TEXT = (
    "🎉 <b>به ربات کصخل خیز خوش اومدین</b> 🎉\n\n"
    "📌 برای استفاده از ربات ابتدا باید عضو کانال "
    "<b>کصخل خیز درجه یک</b> شوید !"
)

NOT_JOINED_TEXT = (
    "🚫 <b>جقی هنوز عضو نشدی</b> 🚫\n\n"
    "داری <b>عضو شدم</b>و میزنی ❓\n"
    "عضو کانال شو ببینم تا نکردمت عه کصکش <b>جقی بدبخت</b> !"
)

JOINED_TEXT = (
    "🎊 <b>بلخره عضو شدی آفرین</b> 🎊\n\n"
    "از <b>جقی بودن</b> دراومدی 😎\n"
    "حالا <b>جنسیتت</b> رو از دکمه های زیر انتخاب کن !"
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
        if db_user and db_user.get("gender"):
            gender_label = {
                "female_have": "💁‍♀ دخترم جنبه دارم",
                "female_dont": "🙅‍♀ دخترم جنبه ندارم",
                "male_have": "🙋‍♂ پسرم جنبه دارم",
                "male_dont": "🙆‍♂ پسرم جنبه ندارم",
            }.get(db_user["gender"], db_user["gender"])
            await update.message.reply_text(
                f"👋 <b>خوش برگشتی {user.first_name}</b>\n\n"
                f"وضعیتت: {gender_label}",
                parse_mode="HTML",
            )
            return
        await update.message.reply_text(
            JOINED_TEXT,
            reply_markup=gender_keyboard(),
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            WELCOME_TEXT,
            reply_markup=join_keyboard(),
            parse_mode="HTML",
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
                parse_mode="HTML",
            )
        except Exception:
            await query.message.reply_text(
                NOT_JOINED_TEXT,
                reply_markup=join_keyboard(),
                parse_mode="HTML",
            )
        await query.answer("🚫 هنوز عضو نشدی!", show_alert=True)
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
        parse_mode="HTML",
    )
    await query.answer("✅ عضو شدی")


async def gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب جنسیت + جنبه"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    mapping = {
        "gender_female_have": ("female_have", "💁‍♀ دخترم جنبه دارم"),
        "gender_female_dont": ("female_dont", "🙅‍♀ دخترم جنبه ندارم"),
        "gender_male_have":   ("male_have",   "🙋‍♂ پسرم جنبه دارم"),
        "gender_male_dont":   ("male_dont",   "🙆‍♂ پسرم جنبه ندارم"),
    }

    if data not in mapping:
        await query.answer()
        return

    gender_value, label = mapping[data]
    set_user_gender(user_id, gender_value)

    try:
        await query.edit_message_text(
            f"✅ <b>ثبت شد:</b> {label}\n\n"
            f"حالا میتونی از ربات استفاده کنی 🎉",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await query.answer(f"✅ ثبت شد: {label}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats - آمار ربات"""
    s = get_stats()
    text = (
        "📊 <b>آمار ربات</b>\n\n"
        f"👥 کل کاربران: <b>{s['total']}</b>\n"
        f"✅ عضو کانال: <b>{s['joined']}</b>\n"
        f"👦 پسر: <b>{s['males']}</b>\n"
        f"👧 دختر: <b>{s['females']}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")
