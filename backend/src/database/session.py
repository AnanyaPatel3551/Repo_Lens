from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.utils.config import settings

# Resolve async driver prefix for PostgreSQL (e.g. Render/Heroku standard env variables)
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# asyncpg doesn't support 'sslmode', replace with 'ssl'
if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=", "ssl=")

# Create database engine with asyncpg driver
engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    echo=False  # Set to True for debugging SQL queries
)

# Async session factory
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Base class for SQLAlchemy declarative models
class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session and closes it when done.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
