# 🤖 ربات خودمونی تلگرام

یه ربات بامزه و خودمونی برای گپ و گعده 🍌🤡

## ✨ امکانات
- پاسخ طنز به `/start` با منشن کاربر
- ذخیره اطلاعات کاربران در دیتابیس SQLite 💾
- دستور `/stats` برای دیدن تعداد کاربران
- دستور `/me` برای دیدن اطلاعات خودت
- آپدیت‌های سالیانه 📅
- پشتیبانی ۲۶ ساعته ⏰
- کاملاً رایگان، بعضی وقتا پولی 😅

## 🚀 نصب و اجرا

```bash
git clone https://github.com/USERNAME/my-telegram-bot.git
cd my-telegram-bot
pip install -r requirements.txt
```

یه فایل `.env` بساز (از `.env.example` کپی کن) و توکن رو داخلش بذار:

```
BOT_TOKEN=your_token_here
```

بعد اجرا کن:

```bash
python bot.py
```

## 📂 ساختار پروژه

```
my-telegram-bot/
├── bot.py              # فایل اصلی ربات
├── database.py         # مدیریت دیتابیس SQLite
├── requirements.txt    # پکیج‌های مورد نیاز
├── .env.example        # نمونه فایل محیطی
├── .gitignore
├── README.md
└── LICENSE
```

## 🛠 دستورات ربات

| دستور | توضیح |
|-------|-------|
| `/start` | شروع و ذخیره اطلاعات کاربر |
| `/stats` | نمایش تعداد کل کاربران |
| `/me` | نمایش اطلاعات ذخیره‌شده خودت |

## 📄 لایسنس
MIT
