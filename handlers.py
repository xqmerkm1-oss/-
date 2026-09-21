from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType

from config import (
    CHANNEL_ID,
    KIR_POINT_REWARD, KOS_POINT_REWARD,
    WEAK_POINT_REWARD, HIGH_POINT_REWARD, TOP_POINT_REWARD,
    KIR_POINT_COOLDOWN,
    KIR_WORD, KOS_WORD, MALE_GOOD_WORD, FEMALE_GOOD_WORD,
    HIGH_WORD, TOP_WORD,
    HIGH_THRESHOLD, TOP_THRESHOLD,
)
from database import (
    create_or_update_user, set_user_joined, set_user_gender,
    log_join_action, get_user, get_stats,
    add_points, can_claim, get_points,
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

MALE_HAVE_TEXT = (
    "🍌 <b>شنیدم دلت کیر میخواد</b> 🍌\n\n"
    "تو می‌تونی یه <b>کصخل بامزه</b> باشی برای به گایی هات برای ایران 🤡\n\n"
    "کیر و کص جمع کن تا بتونی <b>کصخل بهتری</b> باشی\n\n"
    "شمارو بعضی وقتا به تخممون میگیریم\n"
    "عملکردخوب که نه ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی\n"
    "آپدیت های سالیانه میدیم بیرون\n"
    "پشتیبانی <b>۲۶ ساعته</b>"
)

FEMALE_HAVE_TEXT = (
    "🍑 <b>شنیدم دلت کص میخواد</b> 🍑\n\n"
    "تو می‌تونی اینجا به آرزوهات که نه ولی به بهترین <b>کصخل تلگرام</b> تبدیل بشی\n\n"
    "تو اینجا باید کیر و کص جمع کنی تا بتونی <b>کصخل بهتری</b> باشی\n\n"
    "شمارو بعضی وقتا به تخممون میگیریم\n"
    "عملکردخوب که نه ولی تو می‌تونی <b>کصخل نیو</b> داشته باشی\n"
    "آپدیت های سالیانه میدیم بیرون\n"
    "پشتیبانی <b>۲۶ ساعته</b>"
)

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

CONFIRM_TEXT = (
    "✅ <b>حله جنسیتت ثبت شد</b> 🎉\n\n"
    "حالا می‌تونی از ربات <b>استفاده کنی</b> 😎"
)

CANCEL_TEXT = (
    "🤨 <b>میدونستم داری کص میگی</b> 🤨\n\n"
    "دوباره برو <b>جنسیتت</b> رو تایید کن !"
)

# ===== گروه =====
GROUP_WELCOME_TEXT = (
    "🎉 <b>کصخل خیز وارد گروه شده</b> 🍌\n\n"
    "پاشید همگی <b>جق بزنید</b> 💦✊"
)

# ===== راهنمای شومبولی =====
SHOMBOLI_HELP = (
    "📖 <b>راهنمای شومبولی</b>\n\n"

    "🍌 <b>پسر با جنبه؟</b>\n"
    "بنویس <b>کیر</b> → ۵ امتیاز\n\n"

    "🍑 <b>دختر با جنبه؟</b>\n"
    "بنویس <b>کص</b> → ۵ امتیاز\n\n"

    "🌹 <b>پسر بی‌جنبه؟</b>\n"
    "بنویس <b>پسر خوب</b> → ۱ امتیاز\n\n"

    "🌸 <b>دختر بی‌جنبه؟</b>\n"
    "بنویس <b>دختر خوب</b> → ۱ امتیاز\n\n"

    "💎 <b>بالای ۵۰۰۰۰ امتیاز؟</b>\n"
    "بنویس <b>سلام گلم</b> → ۱ امتیاز\n\n"

    "🍰 <b>بالای ۲۰۰۰۰۰ امتیاز؟</b>\n"
    "بنویس <b>کیک</b> → ۱ امتیاز\n\n"

    "⏳ هر ۳ دقیقه یه بار\n\n"

    "🚫 <b>بی‌جنبه‌ها فقط ۱ امتیاز</b>"
)

# ===== پیام‌های خطا =====
NOT_STARTED_TEXT = (
    "❓ <b>اول برو توی ربات استارت بزن</b> ❓\n\n"
    "باید اول توی ربات <b>/start</b> بزنی و <b>جنسیتت</b> رو انتخاب کنی !"
)

KIR_NOT_ALLOWED = (
    "🚫 <b>تو اجازه نداری کیر پوینت بگیری</b> 🚫\n\n"
    "فقط <b>پسرای با جنبه</b> می‌تونن کیر پوینت بگیرن !"
)

KOS_NOT_ALLOWED = (
    "🚫 <b>تو اجازه نداری کص پوینت بگیری</b> 🚫\n\n"
    "فقط <b>دخترای با جنبه</b> می‌تونن کص پوینت بگیرن !"
)

MALE_GOOD_NOT_ALLOWED = (
    "🚫 <b>تو پسر بی‌جنبه نیستی!</b>\n\n"
    "این کلمه فقط برای <b>پسرای بی‌جنبه</b>ست.\n"
    "اگه پسر با جنبه هستی، بنویس <b>کیر</b> 🍌"
)

FEMALE_GOOD_NOT_ALLOWED = (
    "🚫 <b>تو دختر بی‌جنبه نیستی!</b>\n\n"
    "این کلمه فقط برای <b>دخترای بی‌جنبه</b>ست.\n"
    "اگه دختر با جنبه هستی، بنویس <b>کص</b> 🍑"
)

HIGH_NOT_ALLOWED = (
    "💎 <b>این کلمه مخصوص بالای ۵۰۰۰۰ امتیازه!</b>\n\n"
    f"الان امتیازت کمه. برو امتیاز جمع کن !"
)

TOP_NOT_ALLOWED = (
    "🍰 <b>این کلمه مخصوص بالای ۲۰۰۰۰۰ امتیازه!</b>\n\n"
    f"الان امتیازت کمه. برو امتیاز جمع کن !"
)


# ===== توابع کمکی =====

async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID, user_id=user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"[is_member error] {e}")
        return False


# ===== هندلرهای چت خصوصی =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    set_user_gender(user_id, gender_value)

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
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    parts = data.split("_", 1)
    if len(parts) != 2:
        await query.answer()
        return

    action, gender_value = parts

    if action == "confirm":
        set_user_gender(user_id, gender_value)
        try:
            await query.edit_message_text(CONFIRM_TEXT, parse_mode="HTML")
        except Exception:
            pass
        await query.answer("✅ ثبت شد")

    elif action == "cancel":
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
    s = get_stats()
    text = (
        "📊 <b>آمار ربات</b>\n\n"
        f"👥 کل کاربران: <b>{s['total']}</b>\n"
        f"✅ عضو کانال: <b>{s['joined']}</b>\n"
        f"👦 پسر: <b>{s['males']}</b>\n"
        f"👧 دختر: <b>{s['females']}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help - راهنمای شومبولی"""
    await update.message.reply_text(SHOMBOLI_HELP, parse_mode="HTML")


async def my_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mypoints - دیدن امتیازهای خودت"""
    user = update.effective_user
    db_user = get_user(user.id)

    if not db_user or not db_user.get("gender"):
        await update.message.reply_text(NOT_STARTED_TEXT, parse_mode="HTML")
        return

    info = get_points(user.id)
    total = info["points"] if info else 0

    await update.message.reply_text(
        f"📊 <b>امتیازت:</b> {total}\n\n"
        f"🍌 کیر / 🍑 کص → ۵ امتیاز\n"
        f"🌹 پسر خوب / 🌸 دختر خوب → ۱ امتیاز\n"
        f"💎 سلام گلم (بالای ۵۰۰۰۰) → ۱ امتیاز\n"
        f"🍰 کیک (بالای ۲۰۰۰۰۰) → ۱ امتیاز",
        parse_mode="HTML",
    )


# ===== هندلرهای گروه =====

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی ربات به هر گروهی اضافه میشه"""
    message = update.message
    if not message or not message.new_chat_members:
        return

    for member in message.new_chat_members:
        if member.id == context.bot.id:
            await message.reply_text(GROUP_WELCOME_TEXT, parse_mode="HTML")
            await message.reply_text(SHOMBOLI_HELP, parse_mode="HTML")
            return


async def points_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلی امتیاز — همه کلمات رو چک میکنه"""
    message = update.message
    if not message or not message.text:
        return

    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    user = message.from_user
    if not user or user.is_bot:
        return

    text = message.text
    db_user = get_user(user.id)

    # چک استارت خورده یا نه
    if not db_user or not db_user.get("gender"):
        await message.reply_text(NOT_STARTED_TEXT, parse_mode="HTML")
        return

    gender = db_user["gender"]
    info = get_points(user.id)
    current_total = info["points"] if info else 0

    # ===== تعیین کلمه و امتیاز =====
    reward = 0
    matched = False
    reply_emoji = ""

    # 1) پسر با جنبه → کیر
    if KIR_WORD in text:
        if gender == "male_have":
            reward = KIR_POINT_REWARD
            matched = True
            reply_emoji = "🍌"
        else:
            await message.reply_text(KIR_NOT_ALLOWED, parse_mode="HTML")
            return

    # 2) دختر با جنبه → کص
    elif KOS_WORD in text:
        if gender == "female_have":
            reward = KOS_POINT_REWARD
            matched = True
            reply_emoji = "🍑"
        else:
            await message.reply_text(KOS_NOT_ALLOWED, parse_mode="HTML")
            return

    # 3) پسر بی‌جنبه → پسر خوب (فقط ۱ امتیاز)
    elif MALE_GOOD_WORD in text:
        if gender == "male_dont":
            reward = WEAK_POINT_REWARD
            matched = True
            reply_emoji = "🌹"
        else:
            await message.reply_text(MALE_GOOD_NOT_ALLOWED, parse_mode="HTML")
            return

    # 4) دختر بی‌جنبه → دختر خوب (فقط ۱ امتیاز)
    elif FEMALE_GOOD_WORD in text:
        if gender == "female_dont":
            reward = WEAK_POINT_REWARD
            matched = True
            reply_emoji = "🌸"
        else:
            await message.reply_text(FEMALE_GOOD_NOT_ALLOWED, parse_mode="HTML")
            return

    # 5) بالای ۵۰۰۰۰ → سلام گلم
    elif HIGH_WORD in text:
        if current_total < HIGH_THRESHOLD:
            await message.reply_text(HIGH_NOT_ALLOWED, parse_mode="HTML")
            return
        reward = HIGH_POINT_REWARD
        matched = True
        reply_emoji = "💎"

    # 6) بالای ۲۰۰۰۰۰ → کیک
    elif TOP_WORD in text:
        if current_total < TOP_THRESHOLD:
            await message.reply_text(TOP_NOT_ALLOWED, parse_mode="HTML")
            return
        reward = TOP_POINT_REWARD
        matched = True
        reply_emoji = "🍰"

    if not matched:
        return

    # ===== چک کول‌داون =====
    can, remaining = can_claim(user.id, KIR_POINT_COOLDOWN)

    if not can:
        minutes = remaining // 60
        seconds = remaining % 60
        await message.reply_text(
            f"⏳ <b>صبر کن</b> ⏳\n\n"
            f"💰 <b>امتیازت:</b> {current_total}\n\n"
            f"⏰ <b>{minutes} دقیقه و {seconds} ثانیه</b> دیگه می‌تونی دوباره بگیری",
            parse_mode="HTML",
        )
        return

    # ===== اضافه کردن امتیاز =====
    new_total = add_points(user.id, reward)

    await message.reply_text(
        f"{reply_emoji} <b>{reward} امتیاز گرفتی</b> {reply_emoji}\n\n"
        f"💰 <b>امتیازت:</b> {new_total}\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری",
        parse_mode="HTML",
    )
