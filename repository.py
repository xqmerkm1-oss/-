from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select

from database import AsyncSessionLocal
from models import Group, Report, User

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


# ─────────────────────────────────────────────
# کاربر
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# گروه‌ها
# ─────────────────────────────────────────────
async def add_or_update_group(
    group_id: int,
    title: str,
    added_by: int | None = None,
    added_by_name: str | None = None,
    member_count: int = 0,
) -> Group:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).where(Group.group_id == group_id)
        )
        group = result.scalar_one_or_none()

        if group is None:
            group = Group(
                group_id=group_id,
                title=title,
                added_by=added_by,
                added_by_name=added_by_name,
                member_count=member_count,
                is_active=True,
            )
            session.add(group)
        else:
            group.title = title
            group.member_count = member_count
            group.is_active = True
            group.removed_at = None

        await session.commit()
        await session.refresh(group)
        return group


async def mark_group_removed(group_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).where(Group.group_id == group_id)
        )
        group = result.scalar_one_or_none()
        if group is not None:
            group.is_active = False
            group.removed_at = datetime.now(timezone.utc)
            await session.commit()


async def get_all_groups() -> list[Group]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).order_by(desc(Group.added_at))
        )
        return list(result.scalars().all())


async def get_active_groups_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Group.id)).where(Group.is_active == True)
        )
        return result.scalar() or 0


# ─────────────────────────────────────────────
# گزارش‌ها
# ─────────────────────────────────────────────
async def log_report(
    event_type: str,
    description: str | None = None,
    user_id: int | None = None,
    target_id: int | None = None,
    group_id: int | None = None,
) -> Report:
    async with AsyncSessionLocal() as session:
        report = Report(
            event_type=event_type,
            description=description,
            user_id=user_id,
            target_id=target_id,
            group_id=group_id,
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return report


async def get_stats() -> dict:
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)

    async with AsyncSessionLocal() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        users_24h = (
            await session.execute(
                select(func.count(User.id)).where(User.created_at >= yesterday)
            )
        ).scalar() or 0
        users_7d = (
            await session.execute(
                select(func.count(User.id)).where(User.created_at >= last_week)
            )
        ).scalar() or 0

        total_groups = (await session.execute(select(func.count(Group.id)))).scalar() or 0
        active_groups = (
            await session.execute(
                select(func.count(Group.id)).where(Group.is_active == True)
            )
        ).scalar() or 0

        total_attacks = (
            await session.execute(
                select(func.count(Report.id)).where(Report.event_type == "attack")
            )
        ).scalar() or 0
        attacks_24h = (
            await session.execute(
                select(func.count(Report.id)).where(
                    Report.event_type == "attack",
                    Report.created_at >= yesterday,
                )
            )
        ).scalar() or 0

        total_invites = (await session.execute(select(func.sum(User.invite_count)))).scalar() or 0

        total_pads = (await session.execute(select(func.sum(User.pads)))).scalar() or 0
        total_workers = (await session.execute(select(func.sum(User.workers)))).scalar() or 0
        total_lords = (await session.execute(select(func.sum(User.lords)))).scalar() or 0

        return {
            "total_users": total_users,
            "users_24h": users_24h,
            "users_7d": users_7d,
            "total_groups": total_groups,
            "active_groups": active_groups,
            "total_attacks": total_attacks,
            "attacks_24h": attacks_24h,
            "total_invites": total_invites,
            "total_pads": total_pads,
            "total_workers": total_workers,
            "total_lords": total_lords,
        }
