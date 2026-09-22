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

    pads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    bread_used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # 🆕 سیستم دعوت
    invited_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, default=None
    )
    invite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_reward_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
