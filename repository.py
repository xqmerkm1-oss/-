import time
from sqlalchemy import select

from database import AsyncSessionLocal
from models import User

# کش موقت برای ضد اسپم (توی حافظه)
_last_reward: dict[int, float] = {}
COOLDOWN_SECONDS = 60  # هر کاربر هر ۶۰ ثانیه فقط یه بار جایزه می‌گیره


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def add_score_and_title(
    telegram_id: int, points: int, title: str
) -> User | None:
    """امتیاز و لقب کاربر رو آپدیت می‌کنه."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        user.score += points
        user.title = title
        await session.commit()
        await session.refresh(user)
        return user


def is_on_cooldown(telegram_id: int) -> bool:
    """چک می‌کنه کاربر توی زمان انتظار هست یا نه."""
    now = time.time()
    last = _last_reward.get(telegram_id)
    if last is None:
        return False
    return (now - last) < COOLDOWN_SECONDS


def set_cooldown(telegram_id: int) -> None:
    _last_reward[telegram_id] = time.time()
