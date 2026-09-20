import os
import sqlite3
from datetime import datetime

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
            CREATE TABLE IF NOT EXISTS currency (
                user_id INTEGER PRIMARY KEY,
                shombool INTEGER DEFAULT 0,
                chochol INTEGER DEFAULT 0,
                last_shombool_claim TEXT,
                last_chochol_claim TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER PRIMARY KEY,
                warning_count INTEGER DEFAULT 0
            )
        """)
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
        """, (user_id, first_name or "", last_name or "", username or "", now, now))


def save_gender_info(user_id, gender, jense):
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET gender = ?, jense = ? WHERE user_id = ?",
            (gender, jense, user_id)
        )
        return cursor.rowcount > 0


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
        "user_id": row[0], "first_name": row[1], "last_name": row[2],
        "username": row[3], "gender": row[4], "jense": row[5],
        "created_at": row[6], "last_seen": row[7],
    }


def has_gender(user_id):
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT gender, jense FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
    return bool(row and row[0] and row[1])


# ---------- ارزها ----------
def _ensure_currency_row(user_id):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO currency (user_id) VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id,))


def get_shombool(user_id):
    with _connect() as conn:
        cursor = conn.execute("SELECT shombool FROM currency WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


def add_shombool(user_id, amount):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET shombool = shombool + ? WHERE user_id = ?", (amount, user_id))


def reset_shombool(user_id):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET shombool = 0 WHERE user_id = ?", (user_id,))


def get_chochol(user_id):
    with _connect() as conn:
        cursor = conn.execute("SELECT chochol FROM currency WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


def add_chochol(user_id, amount):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET chochol = chochol + ? WHERE user_id = ?", (amount, user_id))


def reset_chochol(user_id):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET chochol = 0 WHERE user_id = ?", (user_id,))


def get_last_shombool_claim(user_id):
    with _connect() as conn:
        cursor = conn.execute("SELECT last_shombool_claim FROM currency WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return None
        try:
            return datetime.fromisoformat(row[0])
        except ValueError:
            return None


def set_last_shombool_claim(user_id, dt):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET last_shombool_claim = ? WHERE user_id = ?", (dt.isoformat(), user_id))


def get_last_chochol_claim(user_id):
    with _connect() as conn:
        cursor = conn.execute("SELECT last_chochol_claim FROM currency WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return None
        try:
            return datetime.fromisoformat(row[0])
        except ValueError:
            return None


def set_last_chochol_claim(user_id, dt):
    _ensure_currency_row(user_id)
    with _connect() as conn:
        conn.execute("UPDATE currency SET last_chochol_claim = ? WHERE user_id = ?", (dt.isoformat(), user_id))


# ---------- ضد سلف ----------
def get_warning_count(user_id):
    with _connect() as conn:
        cursor = conn.execute("SELECT warning_count FROM warnings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


def add_warning(user_id):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO warnings (user_id, warning_count) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET warning_count = warning_count + 1
        """, (user_id,))
        cursor = conn.execute("SELECT warning_count FROM warnings WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]


def reset_warnings(user_id):
    with _connect() as conn:
        conn.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))


# ---------- برترین‌ها ----------
def get_top_shombool(limit=10):
    with _connect() as conn:
        cursor = conn.execute("""
            SELECT c.user_id, c.shombool, u.first_name
            FROM currency c
            LEFT JOIN users u ON u.user_id = c.user_id
            WHERE c.shombool > 0
            ORDER BY c.shombool DESC LIMIT ?
        """, (limit,))
        return cursor.fetchall()


def get_top_chochol(limit=10):
    with _connect() as conn:
        cursor = conn.execute("""
            SELECT c.user_id, c.chochol, u.first_name
            FROM currency c
            LEFT JOIN users u ON u.user_id = c.user_id
            WHERE c.chochol > 0
            ORDER BY c.chochol DESC LIMIT ?
        """, (limit,))
        return cursor.fetchall()
