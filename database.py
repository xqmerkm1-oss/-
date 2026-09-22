from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "?" in url:
        base, _, query = url.partition("?")
        keep = [
            p
            for p in query.split("&")
            if p.startswith(("ssl=", "sslmode=", "options="))
        ]
        url = base + ("?" + "&".join(keep) if keep else "")

    return url


DB_URL = _normalize_db_url(DATABASE_URL)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DB_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
