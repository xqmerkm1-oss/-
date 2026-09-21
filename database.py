import sqlite3
import os
from datetime import datetime, timedelta
from config import DATABASE_PATH


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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

    # ===== جدول کیر پوینت =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kir_points (
            user_id        INTEGER PRIMARY KEY,
            points         INTEGER DEFAULT 0,
            last_claimed   TEXT,
            total_claimed  INTEGER DEFAULT 0,
            updated_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_or_update_user(user_id: int, username: str = None,
                          first_name: str = None, last_name: str = None):
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO join_logs (user_id, action) VALUES (?, ?)",
        (user_id, action),
    )
    conn.commit()
    conn.close()


def get_stats():
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


# ===== کیر پوینت =====

def get_kir_points(user_id: int):
    """گرفتن اطلاعات کیر پوینت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kir_points WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_kir_points(user_id: int, amount: int) -> int:
    """اضافه کردن امتیاز و برگردوندن مجموع جدید"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    # ساخت رکورد اگه وجود نداره
    cursor.execute("""
        INSERT INTO kir_points (user_id, points, last_claimed, total_claimed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            points        = kir_points.points + excluded.points,
            total_claimed = kir_points.total_claimed + excluded.total_claimed,
            last_claimed  = excluded.last_claimed,
            updated_at    = CURRENT_TIMESTAMP
    """, (user_id, amount, now, amount))

    conn.commit()

    cursor.execute("SELECT points FROM kir_points WHERE user_id = ?", (user_id,))
    new_total = cursor.fetchone()["points"]
    conn.close()
    return new_total


def can_claim_kir(user_id: int, cooldown_seconds: int):
    """
    چک میکنه کاربر میتونه امتیاز بگیره یا نه
    Returns: (can_claim: bool, remaining_seconds: int)
    """
    info = get_kir_points(user_id)

    if not info or not info.get("last_claimed"):
        return True, 0

    last = datetime.fromisoformat(info["last_claimed"])
    elapsed = (datetime.now() - last).total_seconds()

    if elapsed >= cooldown_seconds:
        return True, 0

    return False, int(cooldown_seconds - elapsed)
