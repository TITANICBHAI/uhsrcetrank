from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = settings.database_url
is_sqlite = database_url.startswith("sqlite")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
connect_args = {}
if database_url.startswith("postgresql+asyncpg://"):
    parsed_url = make_url(database_url)
    sslmode = parsed_url.query.get("sslmode")
    if sslmode:
        parsed_url = parsed_url.difference_update_query(["sslmode"])
        connect_args["ssl"] = sslmode != "disable"
    database_url = parsed_url
engine = create_async_engine(database_url, echo=False, connect_args=connect_args)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def create_tables() -> None:
    from app.models.db_models import Candidate, Dataset  # noqa: F401
    if is_sqlite:
        database_path = settings.database_url.rsplit("///", 1)[-1]
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)