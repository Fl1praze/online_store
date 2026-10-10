from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase,sessionmaker
from typing import AsyncGenerator

from app.config import settings
engine = create_async_engine(settings.DATABASE_URL)

async_session_maker = sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close()

