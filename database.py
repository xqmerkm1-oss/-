import sqlite3
from datetime import datetime

DB_NAME = "bot_users.db"


def init_db():
    """ساخت جدول کاربران اگه وجود نداشته باشه"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            created_at TEXT,
            last_seen TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_user(user_id: int, first_name: str, last_name: str, username: str):
    """ذخیره یا آپدیت اطلاعات کاربر"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE users
            SET first_name = ?, last_name = ?, username = ?, last_seen = ?
            WHERE user_id = ?
        """, (first_name, last_name, username, now, user_id))
    else:
        cursor.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, first_name, last_name, username, now, now))

    conn.commit()
    conn.close()


def get_user_count() -> int:
    """تعداد کل کاربران"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_user_info(user_id: int):
    """گرفتن اطلاعات یک کاربر خاص"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, first_name, last_name, username, created_at, last_seen
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "username": row[3],
        "created_at": row[4],
        "last_seen": row[5],
    }
