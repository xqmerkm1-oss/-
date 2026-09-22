# 🤖 Shomped Bot

ربات تلگرام شومپد — ساختار تخت و ساده با PostgreSQL.

## 🚀 اجرا با Docker
```bash
cp .env.example .env
# BOT_TOKEN رو داخل .env بذار
docker compose up -d --build
docker compose logs -f bot
```

## 🖥️ اجرای لوکال
```bash
pip install -r requirements.txt
python main.py
```

## 📁 ساختار
همه فایل‌ها توی ریشه پروژه هستن (بدون پوشه `bot/`).
