from datetime import datetime, timezone

from sqlalchemy import desc, select

from database import AsyncSessionLocal
from models import User

COOLDOWN_SECONDS = 180  # ۳ دقیقه


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
