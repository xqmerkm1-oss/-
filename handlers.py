import time
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
    HELP_EXPIRE_SECONDS,
)
from database import (
    create_or_update_user, set_user_joined, set_user_gender,
    log_join_action, get_user, get_stats,
    add_points, can_claim, get_points,
)
from keyboards import (
    join_keyboard, gender_keyboard, confirm_keyboard,
    help_keyboard, help_back_keyboard,
)


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
    "می‌خوای <b>پوینت جمع کنی</b> موفق باشی 🏆"
)

FEMALE_DONT_TEXT = (
    "🌸 <b>سلام خانوم کوچولو</b> 🌸\n\n"
    "شنیدم که با این ربات <b>حال کردی</b> 😄\n\n"
    "منم جات بودم حال میکردم ولی خب 😅\n\n"
    "تو می‌تونی از این ربات استفاده های زیادی بکنی\n"
    "مثلا <b>پوینت جمع کنی</b> به رفیقات <b>پز بدی</b> 💅"
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
    "💎 <b>این کلمه مخصوص بالای ۵۰۰۰۰ پوینته!</b>\n\n"
    f"الان پوینتت کمه. برو پوینت جمع کن !"
)

TOP_NOT_ALLOWED = (
    "🍰 <b>این کلمه مخصوص بالای ۲۰۰۰۰۰ پوینته!</b>\n\n"
    f"الان پوینتت کمه. برو پوینت جمع کن !"
)


# ============================================================
# راهنمای شخصی‌سازی‌شده
# ============================================================

# ===== متن راهنمای کوتاه (شخصی) =====
SHORT_HELP = {
    "male_have": (
        "📖 <b>راهنمای کصخل خیز</b> 📖\n\n"
        "👋 خب پس تو <b>پسر با جنبه</b> هستی!\n\n"
        "🍌 توی گروه بنویس <b>کیر</b> → <b>۵ کیر پوینت</b> بگیر\n\n"
        "⏳ هر ۳ دقیقه یه بار\n\n"
        "👇 برای توضیحات بیشتر، دکمه‌های زیر رو بزن:"
    ),
    "female_have": (
        "📖 <b>راهنمای کصخل خیز</b> 📖\n\n"
        "👋 خب پس تو <b>دختر با جنبه</b> هستی!\n\n"
        "🍑 توی گروه بنویس <b>کص</b> → <b>۵ کص پوینت</b> بگیر\n\n"
        "⏳ هر ۳ دقیقه یه بار\n\n"
        "👇 برای توضیحات بیشتر، دکمه‌های زیر رو بزن:"
    ),
    "male_dont": (
        "📖 <b>راهنمای کصخل خیز</b> 📖\n\n"
        "👋 خب پس تو <b>پسر بی‌جنبه</b> هستی!\n\n"
        "🌹 توی گروه بنویس <b>پسر خوب</b> → <b>۱ پوینت</b> بگیر\n\n"
        "⚠️ چون بی‌جنبه‌ای، دسترسی محدود داری\n\n"
        "👇 برای توضیحات بیشتر، دکمه‌های زیر رو بزن:"
    ),
    "female_dont": (
        "📖 <b>راهنمای کصخل خیز</b> 📖\n\n"
        "👋 خب پس تو <b>دختر بی‌جنبه</b> هستی!\n\n"
        "🌸 توی گروه بنویس <b>دختر خوب</b> → <b>۱ پوینت</b> بگیر\n\n"
        "⚠️ چون بی‌جنبه‌ای، دسترسی محدود داری\n\n"
        "👇 برای توضیحات بیشتر، دکمه‌های زیر رو بزن:"
    ),
}


# ===== متن توضیحات بلند =====
LONG_HELP_TEXT = (
    "📖 <b>راهنمای کصخل خیز — توضیحات بلند</b> 📖\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    "👋 <b>میبینم که تازه واردی...</b>\n\n"
    "ببین بزار برات راحت توضیح بدم:\n\n"

    "😤 <b>مالک دوم از آدم‌های بی‌جنبه خوشش نمیاد</b>، "
    "به خاطر همین تا اونجایی که جا داشته <b>محدودشون کرده</b>. "
    "پس <b>پیشنهاد میدم</b> بی‌جنبه رو انتخاب نکن 🚫\n\n"

    "✅ ولی در عوض برای <b>باجنبه‌ها</b> دسترسی بیشتری گذاشته.\n\n"

    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🎁 <b>کلمات هیجان‌انگیز ماهانه</b>\n\n"

    "شما می‌تونید <b>هر ماه</b> از کلمات هیجان‌انگیز استفاده کنی.\n\n"

    "مثلاً میایم کلمه <b>سلام</b> رو به عنوان <b>کد ماه</b> استفاده می‌کنیم. "
    "هر کی <b>سریع‌تر</b> اون رو پیدا کنه، می‌تونه "
    "<b>کیر پوینت هاشو بیشتر کنه</b> 🍌\n\n"

    "⚠️ ولی این کلمات <b>محدودن</b> و <b>افراد کمی</b> می‌تونن استفاده کنن. "
    "کلاً اگه مثلاً <b>۶۰ نفر</b> استفاده کنن، دیگه کسی نیست که بخواد "
    "استفاده کنه و باید تا <b>ماه بعد</b> صبر کنه ⏳\n\n"

    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 <b>هدف ربات کصخل خیز</b>\n\n"

    "در کل، <b>ربات کصخل خیز</b> یه <b>جایگزین بهتر</b> برای تمام "
    "ربات‌های تلگرامه.\n\n"

    "چون می‌خوایم <b>همه‌ی ربات‌های تلگرامی رو بشکنیم</b> و امیدوارم "
    "مالک ربات‌های دیگه <b>ناراحت نشن</b> 😅\n\n"

    "ولی خب این فقط یه <b>حرفه</b>، هنوز معلوم نیست که این کارو بکنیم. "
    "مگر این که <b>حمایت گسترده</b> داشته باشیم 💪\n\n"

    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📋 <b>کلمه‌ها و پوینت‌ها:</b>\n\n"

    "🍌 <b>پسر با جنبه</b> → <b>کیر</b> → ۵ کیر پوینت\n"
    "🍑 <b>دختر با جنبه</b> → <b>کص</b> → ۵ کص پوینت\n"
    "🌹 <b>پسر بی‌جنبه</b> → <b>پسر خوب</b> → ۱ پوینت\n"
    "🌸 <b>دختر بی‌جنبه</b> → <b>دختر خوب</b> → ۱ پوینت\n"
    "💎 <b>بالای ۵۰۰۰۰</b> → <b>سلام گلم</b> → ۱ پوینت\n"
    "🍰 <b>بالای ۲۰۰۰۰۰</b> → <b>کیک</b> → ۱ پوینت\n\n"

    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⏳ <b>محدودیت زمانی:</b>\n"
    "هر <b>۳ دقیقه</b> یه بار.\n\n"

    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚠️ <b>نکات مهم:</b>\n\n"
    "🚫 اگه <b>بی‌جنبه</b> باشی، <b>فقط ۱ پوینت</b> می‌گیری.\n"
    "🚫 اگه <b>/start</b> نزدی، هیچ پوینتی نمی‌گیری.\n"
    "✅ <b>فقط پسرای با جنبه</b> → کیر پوینت\n"
    "✅ <b>فقط دخترای با جنبه</b> → کص پوینت"
)


# ===== متن‌های اختصاصی هر بخش =====
HELP_KIR_TEXT = (
    "🍌 <b>کیر پوینت</b> 🍌\n\n"
    "👦 فقط <b>پسرای با جنبه</b> می‌تونن بگیرن.\n\n"
    "📝 <b>چطور بگیرم؟</b>\n"
    "توی گروه کلمه <b>کیر</b> رو بنویس.\n\n"
    "💰 <b>چقدر میده؟</b>\n"
    "<b>۵ کیر پوینت</b> هر بار.\n\n"
    "⏳ <b>هر چند وقت؟</b>\n"
    "هر <b>۳ دقیقه</b> یه بار."
)

HELP_KOS_TEXT = (
    "🍑 <b>کص پوینت</b> 🍑\n\n"
    "👧 فقط <b>دخترای با جنبه</b> می‌تونن بگیرن.\n\n"
    "📝 <b>چطور بگیرم؟</b>\n"
    "توی گروه کلمه <b>کص</b> رو بنویس.\n\n"
    "💰 <b>چقدر میده؟</b>\n"
    "<b>۵ کص پوینت</b> هر بار.\n\n"
    "⏳ <b>هر چند وقت؟</b>\n"
    "هر <b>۳ دقیقه</b> یه بار."
)

HELP_MALE_DONT_TEXT = (
    "🌹 <b>پسر بی‌جنبه</b> 🌹\n\n"
    "😐 اگه <b>پسر</b> هستی ولی <b>جنبه نداری</b>.\n\n"
    "📝 <b>چیکار کنم؟</b>\n"
    "توی گروه بنویس <b>پسر خوب</b>.\n\n"
    "💰 <b>چقدر میده؟</b>\n"
    "فقط <b>۱ پوینت</b> هر بار.\n\n"
    "⚠️ چون بی‌جنبه‌ای، دسترسی محدود داری!"
)

HELP_FEMALE_DONT_TEXT = (
    "🌸 <b>دختر بی‌جنبه</b> 🌸\n\n"
    "😐 اگه <b>دختر</b> هستی ولی <b>جنبه نداری</b>.\n\n"
    "📝 <b>چیکار کنم؟</b>\n"
    "توی گروه بنویس <b>دختر خوب</b>.\n\n"
    "💰 <b>چقدر میده؟</b>\n"
    "فقط <b>۱ پوینت</b> هر بار.\n\n"
    "⚠️ چون بی‌جنبه‌ای، دسترسی محدود داری!"
)


# ===== سشن راهنما (برای قفل دکمه‌ها) =====
_help_sessions = {}  # {user_id: timestamp}


def _is_help_valid(user_id: int) -> bool:
    ts = _help_sessions.get(user_id)
    if not ts:
        return False
    return (time.time() - ts) < HELP_EXPIRE_SECONDS


def _create_help_session(user_id: int):
    _help_sessions[user_id] = time.time()


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


async def my_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mypoints - دیدن پوینت‌های خودت"""
    user = update.effective_user
    db_user = get_user(user.id)

    if not db_user or not db_user.get("gender"):
        await update.message.reply_text(NOT_STARTED_TEXT, parse_mode="HTML")
        return

    info = get_points(user.id)
    total = info["points"] if info else 0

    await update.message.reply_text(
        f"💰 <b>پوینتت:</b> {total}\n\n"
        f"🍌 کیر → ۵ کیر پوینت\n"
        f"🍑 کص → ۵ کص پوینت\n"
        f"🌹 پسر خوب → ۱ پوینت\n"
        f"🌸 دختر خوب → ۱ پوینت\n"
        f"💎 سلام گلم (بالای ۵۰۰۰۰) → ۱ پوینت\n"
        f"🍰 کیک (بالای ۲۰۰۰۰۰) → ۱ پوینت",
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
            return


async def rahnama_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر توی گروه کلمه «راهنما» رو نوشت"""
    message = update.message
    if not message or not message.text:
        return

    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if "راهنما" not in message.text:
        return

    user = message.from_user
    db_user = get_user(user.id)

    # اگه استارت نزده
    if not db_user or not db_user.get("gender"):
        await message.reply_text(NOT_STARTED_TEXT, parse_mode="HTML")
        return

    gender = db_user["gender"]

    # ساخت سشن راهنما
    _create_help_session(user.id)

    # ارسال راهنمای کوتاه مخصوص جنسیت
    text = SHORT_HELP.get(gender, SHORT_HELP["male_have"])
    keyboard = help_keyboard(user.id, gender)

    await message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کلیک روی دکمه‌های راهنما"""
    query = update.callback_query
    data = query.data
    clicker_id = query.from_user.id

    # ===== چک امنیت: فقط صاحب راهنما =====
    parts = data.split("_")
    if len(parts) < 3:
        await query.answer()
        return

    # آخرین بخش = user_id صاحب راهنما
    try:
        owner_id = int(parts[-1])
    except ValueError:
        await query.answer()
        return

    if clicker_id != owner_id:
        await query.answer(
            "🚫 تو دسترسی نداری!\n"
            "این پنل فقط برای کسیه که راهنما رو زده.",
            show_alert=True,
        )
        return

    # ===== چک انقضای سشن =====
    if not _is_help_valid(owner_id):
        await query.answer(
            "⏰ این راهنما منقضی شده!\n"
            "دوباره بنویس «راهنما».",
            show_alert=True,
        )
        return

    # ===== تشخیص نوع درخواست =====
    if "long" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "male_have"
        try:
            await query.edit_message_text(
                LONG_HELP_TEXT,
                reply_markup=help_back_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "back" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "male_have"
        text = SHORT_HELP.get(gender, SHORT_HELP["male_have"])
        try:
            await query.edit_message_text(
                text,
                reply_markup=help_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "kir" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "male_have"
        try:
            await query.edit_message_text(
                HELP_KIR_TEXT,
                reply_markup=help_back_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "kos" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "female_have"
        try:
            await query.edit_message_text(
                HELP_KOS_TEXT,
                reply_markup=help_back_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "male_dont" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "male_dont"
        try:
            await query.edit_message_text(
                HELP_MALE_DONT_TEXT,
                reply_markup=help_back_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "female_dont" in data:
        db_user = get_user(owner_id)
        gender = db_user["gender"] if db_user else "female_dont"
        try:
            await query.edit_message_text(
                HELP_FEMALE_DONT_TEXT,
                reply_markup=help_back_keyboard(owner_id, gender),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.answer()

    elif "mypoints" in data:
        info = get_points(owner_id)
        total = info["points"] if info else 0
        await query.answer(f"💰 پوینتت: {total}", show_alert=True)

    else:
        await query.answer()


async def points_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلی پوینت — همه کلمات رو چک میکنه"""
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

    if not db_user or not db_user.get("gender"):
        await message.reply_text(NOT_STARTED_TEXT, parse_mode="HTML")
        return

    gender = db_user["gender"]
    info = get_points(user.id)
    current_total = info["points"] if info else 0

    reward = 0
    matched = False
    emoji = ""
    point_name = ""

    # 1) پسر با جنبه → کیر
    if KIR_WORD in text:
        if gender == "male_have":
            reward = KIR_POINT_REWARD
            matched = True
            emoji = "🍌"
            point_name = "کیر پوینت"
        else:
            await message.reply_text(KIR_NOT_ALLOWED, parse_mode="HTML")
            return

    # 2) دختر با جنبه → کص
    elif KOS_WORD in text:
        if gender == "female_have":
            reward = KOS_POINT_REWARD
            matched = True
            emoji = "🍑"
            point_name = "کص پوینت"
        else:
            await message.reply_text(KOS_NOT_ALLOWED, parse_mode="HTML")
            return

    # 3) پسر بی‌جنبه → پسر خوب
    elif MALE_GOOD_WORD in text:
        if gender == "male_dont":
            reward = WEAK_POINT_REWARD
            matched = True
            emoji = "🌹"
            point_name = "پسر خوب پوینت"
        else:
            await message.reply_text(MALE_GOOD_NOT_ALLOWED, parse_mode="HTML")
            return

    # 4) دختر بی‌جنبه → دختر خوب
    elif FEMALE_GOOD_WORD in text:
        if gender == "female_dont":
            reward = WEAK_POINT_REWARD
            matched = True
            emoji = "🌸"
            point_name = "دختر خوب پوینت"
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
        emoji = "💎"
        point_name = "سلام گلم پوینت"

    # 6) بالای ۲۰۰۰۰۰ → کیک
    elif TOP_WORD in text:
        if current_total < TOP_THRESHOLD:
            await message.reply_text(TOP_NOT_ALLOWED, parse_mode="HTML")
            return
        reward = TOP_POINT_REWARD
        matched = True
        emoji = "🍰"
        point_name = "کیک پوینت"

    if not matched:
        return

    can, remaining = can_claim(user.id, KIR_POINT_COOLDOWN)

    if not can:
        minutes = remaining // 60
        seconds = remaining % 60
        await message.reply_text(
            f"⏳ <b>صبر کن</b> ⏳\n\n"
            f"{emoji} <b>{point_name} هات :</b> {current_total}\n\n"
            f"⏰ <b>{minutes} دقیقه و {seconds} ثانیه</b> دیگه می‌تونی دوباره بگیری",
            parse_mode="HTML",
        )
        return

    new_total = add_points(user.id, reward)

    await message.reply_text(
        f"{emoji} <b>{reward} {point_name} گرفتی</b> {emoji}\n\n"
        f"💰 <b>{point_name} هات :</b> {new_total}\n\n"
        f"⏳ <b>۳ دقیقه</b> دیگه می‌تونی دوباره بگیری",
        parse_mode="HTML",
    )
