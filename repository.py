from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select

from database import AsyncSessionLocal
from models import User

COOLDOWN_SECONDS = 180

WORKER_FOOD_MEAT = 1
LORD_FOOD_CAKE = 3
HUNGRY_DAYS_LIMIT = 7


RESOURCE_MAP = {
    "پد": "pads",
    "پدها": "pads",
    "گوشت": "meat",
    "چای": "tea",
    "آجر": "bricks",
    "اجر": "bricks",
    "نون بربری": "bread_count",
    "نون": "bread_count",
    "کیک یزدی": "cake",
    "کیک": "cake",
    "سیفید": "shields",
    "کارگر افغانی": "workers",
    "کارگرافغانی": "workers",
    "افغانی": "workers",
    "کارگر": "workers",
    "لر": "lords",
    "لرها": "lords",
    "گل رز": "pad_rose",
    "گلرز": "pad_rose",
    "دختر خوب": "pad_girl",
    "دخترخوب": "pad_girl",
    "پسر خوب": "pad_boy",
    "پسرخوب": "pad_boy",
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
            last_fed_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True


async def get_or_create_user_by_id(telegram_id: int) -> tuple[User | None, bool]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is not None:
            return user, False

        user = User(
            telegram_id=telegram_id,
            last_fed_at=datetime.now(timezone.utc),
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
    hungry_days: int | None = None,
    last_fed_at: datetime | None = None,
) -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        if meat is not None:
            user.meat = meat
        if tea is not None:
            user.tea = tea
        if bricks is not None:
            user.bricks = bricks
        if bread_count is not None:
            user.bread_count = bread_count
        if cake is not None:
            user.cake = cake
        if shields is not None:
            user.shields = shields
        if workers is not None:
            user.workers = workers
        if lords is not None:
            user.lords = lords
        if pad_rose is not None:
            user.pad_rose = pad_rose
        if pad_girl is not None:
            user.pad_girl = pad_girl
        if pad_boy is not None:
            user.pad_boy = pad_boy
        if pad_candle is not None:
            user.pad_candle = pad_candle
        if hungry_days is not None:
            user.hungry_days = hungry_days
        if last_fed_at is not None:
            user.last_fed_at = last_fed_at

        await session.commit()
        await session.refresh(user)
        return user


async def process_daily_food(telegram_id: int) -> dict:
    result_data = {
        "processed": False,
        "days": 0,
        "meat_needed": 0,
        "cake_needed": 0,
        "starved": False,
        "workers_lost": 0,
        "lords_lost": 0,
    }

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return result_data

        if user.workers <= 0 and user.lords <= 0:
            user.last_fed_at = datetime.now(timezone.utc)
            user.hungry_days = 0
            await session.commit()
            return result_data

        now = datetime.now(timezone.utc)
        last_fed = user.last_fed_at

        if last_fed is None:
            user.last_fed_at = now
            await session.commit()
            return result_data

        if last_fed.tzinfo is None:
            last_fed = last_fed.replace(tzinfo=timezone.utc)

        elapsed = now - last_fed
        days_passed = int(elapsed.total_seconds() // 86400)

        if days_passed < 1:
            return result_data

        result_data["processed"] = True
        result_data["days"] = days_passed

        for _ in range(days_passed):
            meat_needed = user.workers * WORKER_FOOD_MEAT
            cake_needed = user.lords * LORD_FOOD_CAKE

            result_data["meat_needed"] = meat_needed
            result_data["cake_needed"] = cake_needed

            if user.meat >= meat_needed and user.cake >= cake_needed:
                user.meat -= meat_needed
                user.cake -= cake_needed
                user.hungry_days = 0
            else:
                user.hungry_days += 1

                if user.hungry_days >= HUNGRY_DAYS_LIMIT:
                    result_data["starved"] = True
                    result_data["workers_lost"] = user.workers
                    result_data["lords_lost"] = user.lords
                    user.workers = 0
                    user.lords = 0
                    user.hungry_days = 0
                    break

        user.last_fed_at = now
        await session.commit()
        return result_data


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
