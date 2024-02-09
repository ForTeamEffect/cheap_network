from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from project.settings import pg_user, pg_password, pg_address, pg_port, pg_server_name
from .models import Base


DATABASE_URI = f'postgresql+asyncpg://{pg_user}:{pg_password}@{pg_address}:{pg_port}/{pg_server_name}'

engine = create_async_engine(DATABASE_URI)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
