import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from config import DATABASE_URL


def get_connection():
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL تنظیم نشده! برو توی Railway → Variables → "
            "DATABASE_URL رو با Reference از Postgres ست کن."
        )
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      BIGINT PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            last_name    TEXT,
            gender       TEXT,
            is_joined    INTEGER DEFAULT 0,
            joined_at    TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_logs (
            id         SERIAL PRIMARY KEY,
            user_id    BIGINT,
            action     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS points (
            user_id        BIGINT PRIMARY KEY,
            points         INTEGER DEFAULT 0,
            last_claimed   TEXT,
            total_claimed  INTEGER DEFAULT 0,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def create_or_update_user(user_id: int, username: str = None,
                          first_name: str = None, last_name: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name  = EXCLUDED.last_name,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, username, first_name, last_name))
    conn.commit()
    cursor.close()
    conn.close()


def set_user_joined(user_id: int, joined: bool):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat() if joined else None
    cursor.execute("""
        UPDATE users
        SET is_joined = %s, joined_at = COALESCE(%s, joined_at),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (1 if joined else 0, now, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def set_user_gender(user_id: int, gender: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET gender = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (gender, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def log_join_action(user_id: int, action: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO join_logs (user_id, action) VALUES (%s, %s)",
        (user_id, action),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_stats():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS joined FROM users WHERE is_joined = 1")
    joined = cursor.fetchone()["joined"]

    cursor.execute("SELECT COUNT(*) AS males FROM users WHERE gender LIKE 'male_%'")
    males = cursor.fetchone()["males"]

    cursor.execute("SELECT COUNT(*) AS females FROM users WHERE gender LIKE 'female_%'")
    females = cursor.fetchone()["females"]

    cursor.close()
    conn.close()
    return {
        "total": total,
        "joined": joined,
        "males": males,
        "females": females,
    }


def get_points(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM points WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def add_points(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO points (user_id, points, last_claimed, total_claimed)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            points        = points.points + EXCLUDED.points,
            total_claimed = points.total_claimed + EXCLUDED.total_claimed,
            last_claimed  = EXCLUDED.last_claimed,
            updated_at    = CURRENT_TIMESTAMP
    """, (user_id, amount, now, amount))

    conn.commit()

    cursor.execute("SELECT points FROM points WHERE user_id = %s", (user_id,))
    new_total = cursor.fetchone()["points"]
    cursor.close()
    conn.close()
    return new_total


def can_claim(user_id: int, cooldown_seconds: int):
    """Returns: (can_claim: bool, remaining_seconds: int)"""
    info = get_points(user_id)

    if not info or not info.get("last_claimed"):
        return True, 0

    last = datetime.fromisoformat(info["last_claimed"])
    elapsed = (datetime.now() - last).total_seconds()

    if elapsed >= cooldown_seconds:
        return True, 0

    return False, int(cooldown_seconds - elapsed)
