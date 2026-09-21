from telegram import Update
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from database import (
    create_or_update_user, set_user_joined, set_user_gender,
    log_join_action, get_user, get_stats,
)
from keyboards import join_keyboard, gender_keyboard, confirm_keyboard


# ===== متن‌ها =====
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

# ===== متن دکمه‌های جنبه دارم =====
MALE_HAVE_TEXT = (
    "🍌 <b>شنیدم دلت کیر میخواد</b> 🍌\n\n"
    "تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به گایی هات برای ایران 🤡\n\n"
    "کیر و کص جمع کن تا بتونی <b>کصخل بهتری</b> باشی\n\n"
    "شنیدم دلت کیر میخواد🍌\n"
    "تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به گایی هات برای ایران 🤡\n\n"
    "کیر و کص جمع کن تا بتونی <b>کصخل بهتری</b> باشی\n\n"
    "شمارو بعضی وقتا به تخممون میگیریم\n"
    "عملکردخوب که نه ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی\n"
    "آپدیت های سالیانه میدیم بیرون\n"
    "مثل شما می‌تونیم یه کصخل باشیم\n"
    "پشتیبانی <b>۲۶ ساعته</b>\n"
    "کاملا رایگان بعضی وقتا پولی"
)

FEMALE_HAVE_TEXT = (
    "🍑 <b>شنیدم دلت کص میخواد</b> 🍑\n\n"
    "تو می‌تونی اینجا به آرزوهات که نه ولی به بهترین <b>کصخل تلگرام</b> تبدیل بشی\n\n"
    "تو اینجا باید کیر و کص جمع کنی تا بتونی <b>کصخل بهتری</b> باشی\n\n"
    "شمارو بعضی وقتا به تخممون میگیریم\n"
    "عملکردخوب که نه ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی\n"
    "آپدیت های سالیانه میدیم بیرون\n"
    "مثل شما می‌تونیم یه کصخل باشیم\n"
    "پشتیبانی <b>۲۶ ساعته</b>\n"
    "کاملا رایگان بعضی وقتا پولی"
)

# ===== متن دکمه‌های جنبه ندارم =====
MALE_DONT_TEXT = (
    "🌹 <b>سلام گل پسر</b> 🌹\n\n"
    "شنیدم که از این ربات ما <b>خوشت اومده</b> 😏\n\n"
    "می‌خوای عوض این ربات بشی <b>موفق باشی</b> 🎯\n\n"
    "می‌خوای <b>امتیاز جمع کنی</b> موفق باشی 🏆"
)

FEMALE_DONT_TEXT = (
    "🌸 <b>سلام خانوم کوچولو</b> 🌸\n\n"
    "شنیدم که با این ربات <b>حال کردی</b> 😄\n\n"
    "منم جات بودم حال میکردم ولی خب 😅\n\n"
    "تو می‌تونی از این ربات استفاده های زیادی بکنی\n"
    "مثلا <b>امتیاز جمع کنی</b> به رفیقات <b>پز بدی</b> 💅"
)

# ===== متن‌های تأیید / انصراف =====
CONFIRM_TEXT = "✅ <b>حله جنسیتت ثبت شد</b> 🎉"

CANCEL_TEXT = (
    "🤨 <b>میدونستم داری کص میگی</b> 🤨\n\n"
    "دوباره برو <b>جنسیتت</b> رو تایید کن !"
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
                "male_have":   "🙋‍♂ پسرم جنبه دارم",
                "male_dont":   "🙆‍♂ پسرم جنبه ندارم",
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
    """انتخاب جنسیت → نمایش متن + دکمه‌های تأیید"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    mapping = {
        "gender_male_have":   ("male_have",   MALE_HAVE_TEXT),
        "gender_female_have": ("female_have", FEMALE_HAVE_TEXT),
        "gender_male_dont":   ("male_dont",   MALE_DONT_TEXT),
        "gender_female_dont": ("female_dont", FEMALE_DONT_TEXT),
    }

    if data not in mapping:
        await query.answer()
        return

    gender_value, response_text = mapping[data]

    # ذخیره موقت جنسیت (هنوز تایید نشده)
    set_user_gender(user_id, gender_value)

    # ویرایش پیام با متن + دکمه‌های تأیید
    try:
        await query.edit_message_text(
            response_text,
            reply_markup=confirm_keyboard(gender_value),
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"[gender_choice error] {e}")
        try:
            await query.message.reply_text(
                response_text,
                reply_markup=confirm_keyboard(gender_value),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await query.answer()


async def confirm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید یا انصراف نهایی"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data  # مثل confirm_male_have یا cancel_male_have

    parts = data.split("_", 1)
    if len(parts) != 2:
        await query.answer()
        return

    action, gender_value = parts  # action = confirm یا cancel

    if action == "confirm":
        # کاربر تأیید کرد → ثبت نهایی
        set_user_gender(user_id, gender_value)
        try:
            await query.edit_message_text(
                CONFIRM_TEXT,
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer("✅ ثبت شد")

    elif action == "cancel":
        # کاربر انصراف داد → برگرد به دکمه‌های جنسیت
        try:
            await query.edit_message_text(
                CANCEL_TEXT,
                reply_markup=gender_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer("❌ دوباره انتخاب کن")


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
