import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    """اتصال به دیتابیس با ساخت پوشه در صورت نبود"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """ساخت جدول‌ها"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            last_name    TEXT,
            gender       TEXT,
            is_joined    INTEGER DEFAULT 0,
            joined_at    TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            action     TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id: int):
    """گرفتن اطلاعات یک کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_or_update_user(user_id: int, username: str = None,
                          first_name: str = None, last_name: str = None):
    """ساخت یا آپدیت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()


def set_user_joined(user_id: int, joined: bool):
    """ثبت وضعیت عضویت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat() if joined else None
    cursor.execute("""
        UPDATE users
        SET is_joined = ?, joined_at = COALESCE(?, joined_at),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (1 if joined else 0, now, user_id))
    conn.commit()
    conn.close()


def set_user_gender(user_id: int, gender: str):
    """ثبت جنسیت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET gender = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (gender, user_id))
    conn.commit()
    conn.close()


def log_join_action(user_id: int, action: str):
    """لاگ کردن اکشن عضویت"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO join_logs (user_id, action) VALUES (?, ?)",
        (user_id, action),
    )
    conn.commit()
    conn.close()


def get_stats():
    """آمار کلی ربات"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS joined FROM users WHERE is_joined = 1")
    joined = cursor.fetchone()["joined"]

    cursor.execute("SELECT COUNT(*) AS males FROM users WHERE gender LIKE 'male_%'")
    males = cursor.fetchone()["males"]

    cursor.execute("SELECT COUNT(*) AS females FROM users WHERE gender LIKE 'female_%'")
    females = cursor.fetchone()["females"]

    conn.close()
    return {
        "total": total,
        "joined": joined,
        "males": males,
        "females": females,
    }
