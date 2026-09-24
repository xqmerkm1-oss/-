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

    pads: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bread_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    meat: Mapped[int] = mapped_column(BigInteger, default=200, nullable=False)
    tea: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)
    bricks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bread_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cake: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    shields: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    pad_rose: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_girl: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_boy: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    pad_candle: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    workers: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    lords: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    hungry_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_fed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    invited_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, default=None
    )
    invite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_reward_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_shield_shown: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_by_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
