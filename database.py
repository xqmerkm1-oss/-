import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id          BIGINT PRIMARY KEY,
            warning_count    INTEGER DEFAULT 0,
            restricted_until TEXT,
            last_warning     TEXT,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            user_id          BIGINT PRIMARY KEY,
            last_activity    TEXT,
            inactive_since   TEXT,
            is_inactive      INTEGER DEFAULT 0,
            last_reminder    TEXT,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ===== کاربران =====

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


# ===== پوینت‌ها =====

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


def subtract_points(user_id: int, amount: int) -> int:
    """کسر پوینت (حداقل ۰)"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        UPDATE points
        SET points = GREATEST(points - %s, 0),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (amount, user_id))

    conn.commit()

    cursor.execute("SELECT points FROM points WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    new_total = row["points"] if row else 0
    cursor.close()
    conn.close()
    return new_total


def can_claim(user_id: int, cooldown_seconds: int):
    info = get_points(user_id)

    if not info or not info.get("last_claimed"):
        return True, 0

    last = datetime.fromisoformat(info["last_claimed"])
    elapsed = (datetime.now() - last).total_seconds()

    if elapsed >= cooldown_seconds:
        return True, 0

    return False, int(cooldown_seconds - elapsed)


# ===== اخطارها (سلف) =====

def get_warning(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM warnings WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def add_warning(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO warnings (user_id, warning_count, last_warning)
        VALUES (%s, 1, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            warning_count = warnings.warning_count + 1,
            last_warning  = EXCLUDED.last_warning,
            updated_at    = CURRENT_TIMESTAMP
    """, (user_id, now))

    conn.commit()

    cursor.execute("SELECT warning_count FROM warnings WHERE user_id = %s", (user_id,))
    count = cursor.fetchone()["warning_count"]
    cursor.close()
    conn.close()
    return count


def restrict_user(user_id: int, hours: int = 24):
    conn = get_connection()
    cursor = conn.cursor()
    until = (datetime.now() + timedelta(hours=hours)).isoformat()

    cursor.execute("""
        INSERT INTO warnings (user_id, warning_count, restricted_until)
        VALUES (%s, 0, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            restricted_until = EXCLUDED.restricted_until,
            warning_count    = 0,
            updated_at       = CURRENT_TIMESTAMP
    """, (user_id, until))

    conn.commit()
    cursor.close()
    conn.close()


def is_restricted(user_id: int):
    info = get_warning(user_id)

    if not info or not info.get("restricted_until"):
        return False, 0

    until = datetime.fromisoformat(info["restricted_until"])
    now = datetime.now()

    if now >= until:
        return False, 0

    remaining = int((until - now).total_seconds())
    return True, remaining


# ===== فعالیت =====

def update_activity(user_id: int):
    """آپدیت آخرین فعالیت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO activity (user_id, last_activity)
        VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            last_activity  = EXCLUDED.last_activity,
            is_inactive    = 0,
            inactive_since = NULL,
            updated_at     = CURRENT_TIMESTAMP
    """, (user_id, now))
    conn.commit()
    cursor.close()
    conn.close()


def get_inactive_users(days: int = 3):
    """کاربرانی که N روز فعالیت نکردن"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    threshold = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute("""
        SELECT u.user_id, u.first_name, a.last_activity
        FROM users u
        LEFT JOIN activity a ON u.user_id = a.user_id
        WHERE (a.last_activity IS NULL OR a.last_activity < %s)
          AND (a.is_inactive IS NULL OR a.is_inactive = 0)
          AND u.gender IS NOT NULL
    """, (threshold,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]


def mark_inactive(user_id: int):
    """علامت‌گذاری کاربر به عنوان غیرفعال"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO activity (user_id, is_inactive, inactive_since, last_reminder)
        VALUES (%s, 1, %s, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            is_inactive    = 1,
            inactive_since = COALESCE(activity.inactive_since, EXCLUDED.inactive_since),
            last_reminder  = EXCLUDED.last_reminder,
            updated_at     = CURRENT_TIMESTAMP
    """, (user_id, now, now))
    conn.commit()
    cursor.close()
    conn.close()


def get_inactive_list():
    """کاربرانی که در حالت غیرفعال هستن"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT user_id, inactive_since
        FROM activity
        WHERE is_inactive = 1
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(r) for r in rows]
