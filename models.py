from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # پد اصلی
    pads: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bread_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # منابع
    meat: Mapped[int] = mapped_column(BigInteger, default=200, nullable=False)
    tea: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)
    bricks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bread_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cake: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    shields: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # منبع‌های تکی
    pad_rose: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_girl: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_boy: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_candle: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # جنگجوها
    workers: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    lords: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # گرسنگی
    hungry_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_fed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # دعوت
    invited_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, default=None
    )
    invite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # زمان‌ها
    last_reward_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_shield_shown: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
