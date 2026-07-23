from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Inisialisasi async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Ubah ke True jika ingin melihat raw SQL log di console
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

# Inisialisasi async sessionmaker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Dependency generator untuk di-inject ke route FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
