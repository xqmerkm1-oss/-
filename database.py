import os
import sqlite3
from datetime import datetime

# مسیر دیتابیس
DB_NAME = os.getenv("DB_PATH", "bot_users.db")

_db_dir = os.path.dirname(DB_NAME)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


def _connect():
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
                jense TEXT,
                created_at TEXT,
                last_seen TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shombool (
                user_id INTEGER PRIMARY KEY,
                amount INTEGER DEFAULT 0,
                last_claim TEXT
            )
        """)
        # اضافه کردن ستون jense برای دیتابیس قدیمی
        try:
            conn.execute("ALTER TABLE users ADD COLUMN jense TEXT")
        except sqlite3.OperationalError:
            pass


# ---------- کاربران ----------
def save_user(user_id, first_name, last_name, username):
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


def save_gender_info(user_id, gender, jense):
    """ثبت جنسیت + جنبه."""
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET gender = ?, jense = ? WHERE user_id = ?",
            (gender, jense, user_id)
        )
        return cursor.rowcount > 0


def get_user_count():
    with _connect() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


def get_user_info(user_id):
    with _connect() as conn:
        cursor = conn.execute("""
            SELECT user_id, first_name, last_name, username, gender, jense, created_at, last_seen
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
        "jense": row[5],
        "created_at": row[6],
        "last_seen": row[7],
    }


# ---------- شومبول ----------
def get_shombool(user_id):
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT amount FROM shombool WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0


def add_shombool(user_id, amount):
    """اضافه کردن شومبول. هر بار درست جمع می‌شه."""
    with _connect() as conn:
        # اول مطمئن شو رکورد وجود داره
        conn.execute("""
            INSERT INTO shombool (user_id, amount)
            VALUES (?, 0)
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id,))
        # بعد مقدار رو اضافه کن
        conn.execute("""
            UPDATE shombool
            SET amount = amount + ?
            WHERE user_id = ?
        """, (amount, user_id))


def get_last_claim(user_id):
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT last_claim FROM shombool WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return None
        try:
            return datetime.fromisoformat(row[0])
        except ValueError:
            return None


def set_last_claim(user_id, dt):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO shombool (user_id, amount, last_claim)
            VALUES (?, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_claim = excluded.last_claim
        """, (user_id, dt.isoformat()))


def get_top_shombool(limit=10):
    with _connect() as conn:
        cursor = conn.execute("""
            SELECT s.user_id, s.amount, u.first_name
            FROM shombool s
            LEFT JOIN users u ON u.user_id = s.user_id
            ORDER BY s.amount DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
