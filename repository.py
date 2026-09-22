from datetime import datetime, timezone

from sqlalchemy import desc, select

from database import AsyncSessionLocal
from models import User

COOLDOWN_SECONDS = 180  # ۳ دقیقه


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    invited_by: int | None = None,
) -> tuple[User, bool]:
    """کاربر رو می‌گیره یا می‌سازه.
    مقدار برگشتی: (کاربر, آیا تازه ساخته شد؟)
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is not None:
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            invited_by=invited_by,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True


async def add_pads(telegram_id: int, amount: int) -> None:
    """به کاربر پد اضافه می‌کنه."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.pads += amount
            await session.commit()


async def increment_invite_count(telegram_id: int) -> None:
    """تعداد دعوت‌های موفق کاربر رو یکی زیاد می‌کنه."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.invite_count += 1
            await session.commit()


async def give_reward(telegram_id: int, points: int) -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        user.pads += points
        user.last_reward_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)
        return user


async def mark_bread_used(telegram_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.bread_used = True
            await session.commit()


def seconds_remaining(user: User) -> int:
    if user.last_reward_at is None:
        return 0

    now = datetime.now(timezone.utc)
    last = user.last_reward_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    elapsed = (now - last).total_seconds()
    remaining = COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining))


async def get_top_users(limit: int = 10) -> list[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(desc(User.pads)).limit(limit)
        )
        return list(result.scalars().all())
