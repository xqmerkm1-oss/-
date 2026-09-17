import os
import sqlite3
from datetime import datetime

# مسیر دیتابیس: قابل تنظیم با متغیر محیطی، پیش‌فرض کنار پروژه
DB_NAME = os.getenv("DB_PATH", "bot_users.db")

# اطمینان از وجود پوشه‌ی دیتابیس (اگه مسیر پوشه داشته باشه)
_db_dir = os.path.dirname(DB_NAME)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


def _connect():
    """اتصال به دیتابیس با WAL برای عملکرد بهتر."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                gender TEXT,
                created_at TEXT,
                last_seen TEXT
            )
        """)


def save_user(user_id, first_name, last_name, username):
    """ذخیره یا آپدیت کاربر با UPSERT."""
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                username   = excluded.username,
                last_seen  = excluded.last_seen
        """, (
            user_id,
            first_name or "",
            last_name or "",
            username or "",
            now,
            now,
        ))


def save_gender(user_id, gender):
    """ثبت جنسیت. اگه کاربر وجود نداشت، False برمی‌گردونه."""
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET gender = ? WHERE user_id = ?",
            (gender, user_id)
        )
        return cursor.rowcount > 0


def get_user_count():
    with _connect() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


def get_user_info(user_id):
    with _connect() as conn:
        cursor = conn.execute("""
            SELECT user_id, first_name, last_name, username, gender, created_at, last_seen
            FROM users WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "user_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "username": row[3],
        "gender": row[4],
        "created_at": row[5],
        "last_seen": row[6],
    }
