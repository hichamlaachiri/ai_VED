from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _ensure_column(conn, table: str, column: str, col_type: str):
    """Safely adds a column to an existing SQLite table if it does not exist."""
    res = await conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in res.fetchall()}
    if column not in existing:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent schema upgrades for existing SQLite databases
        await _ensure_column(conn, "episodes", "outline_summary", "TEXT")
        await _ensure_column(conn, "episodes", "continuity_notes", "TEXT")
        await _ensure_column(conn, "shots", "props_continuity", "TEXT")
        await _ensure_column(conn, "shots", "dialogue_lines_json", "TEXT")
