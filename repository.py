from datetime import datetime, timezone

from sqlalchemy import desc, select

from database import AsyncSessionLocal
from models import User

COOLDOWN_SECONDS = 180


# 🎯 نقشه‌ی اسم منبع به ستون دیتابیس
RESOURCE_MAP = {
    "پد": "pads",
    "گوشت": "meat",
    "چای": "tea",
    "آجر": "bricks",
    "نون بربری": "bread_count",
    "کیک یزدی": "cake",
    "سیفید": "shields",
    "کارگر افغانی": "workers",
    "لر": "lords",
    "گل رز": "pad_rose",
    "دختر خوب": "pad_girl",
    "پسر خوب": "pad_boy",
    "شمع": "pad_candle",
}


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    invited_by: int | None = None,
) -> tuple[User, bool]:
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


async def get_user_by_id(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_user_by_username(username: str) -> User | None:
    username = username.lstrip("@")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()


async def add_pads(telegram_id: int, amount: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.pads += amount
            await session.commit()


async def set_user_pads(telegram_id: int, amount: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.pads = amount
        await session.commit()
        return True


async def increment_invite_count(telegram_id: int) -> None:
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


async def update_resources(
    telegram_id: int,
    meat: int | None = None,
    tea: int | None = None,
    bricks: int | None = None,
    bread_count: int | None = None,
    cake: int | None = None,
    shields: int | None = None,
    workers: int | None = None,
    lords: int | None = None,
    pad_rose: int | None = None,
    pad_girl: int | None = None,
    pad_boy: int | None = None,
    pad_candle: int | None = None,
) -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        if meat is not None:
            user.meat = max(0, meat)
        if tea is not None:
            user.tea = max(0, tea)
        if bricks is not None:
            user.bricks = max(0, bricks)
        if bread_count is not None:
            user.bread_count = max(0, bread_count)
        if cake is not None:
            user.cake = max(0, cake)
        if shields is not None:
            user.shields = max(0, shields)
        if workers is not None:
            user.workers = max(0, workers)
        if lords is not None:
            user.lords = max(0, lords)
        if pad_rose is not None:
            user.pad_rose = max(0, pad_rose)
        if pad_girl is not None:
            user.pad_girl = max(0, pad_girl)
        if pad_boy is not None:
            user.pad_boy = max(0, pad_boy)
        if pad_candle is not None:
            user.pad_candle = max(0, pad_candle)

        await session.commit()
        await session.refresh(user)
        return user


async def transfer_shields(from_id: int, to_id: int, amount: int) -> bool:
    async with AsyncSessionLocal() as session:
        r1 = await session.execute(select(User).where(User.telegram_id == from_id))
        sender = r1.scalar_one_or_none()
        if sender is None or sender.shields < amount:
            return False

        r2 = await session.execute(select(User).where(User.telegram_id == to_id))
        receiver = r2.scalar_one_or_none()
        if receiver is None:
            return False

        sender.shields -= amount
        receiver.shields += amount
        await session.commit()
        return True


async def transfer_resource(
    from_id: int, to_id: int, resource_name: str, amount: int
) -> tuple[bool, int, int]:
    """منبع رو از یه کاربر به کاربر دیگه منتقل می‌کنه.

    مقدار برگشتی: (موفق؟, مقدار جدید فرستنده, مقدار جدید گیرنده)
    """
    column = RESOURCE_MAP.get(resource_name)
    if column is None:
        return False, 0, 0

    async with AsyncSessionLocal() as session:
        r1 = await session.execute(select(User).where(User.telegram_id == from_id))
        sender = r1.scalar_one_or_none()
        if sender is None:
            return False, 0, 0

        r2 = await session.execute(select(User).where(User.telegram_id == to_id))
        receiver = r2.scalar_one_or_none()
        if receiver is None:
            return False, 0, 0

        sender_val = getattr(sender, column)
        receiver_val = getattr(receiver, column)

        setattr(sender, column, sender_val - amount)
        setattr(receiver, column, receiver_val + amount)

        await session.commit()

        return True, sender_val - amount, receiver_val + amount


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


async def get_random_user_in_group(
    context, chat_id: int, exclude_id: int
) -> User | None:
    import random

    top = await get_top_users(20)
    candidates = [u for u in top if u.telegram_id != exclude_id]
    if not candidates:
        return None
    return random.choice(candidates)
