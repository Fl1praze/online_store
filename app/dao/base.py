from sqlalchemy import select, insert,update,delete
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
     model = None

     @classmethod
     async def add(cls, session: AsyncSession, **data):
         query = insert(cls.model).values(**data)
         result = await session.execute(query)
         await session.flush()
         return result.inserted_primary_key[0] if result.inserted_primary_key else None


     @classmethod
     async def find_by_id(cls, session: AsyncSession, model_id:int):
         query = select(cls.model).filter_by(id=model_id)
         result = await session.execute(query)
         return result.scalar_one_or_none()

     @classmethod
     async def delete(cls, session: AsyncSession, model_id: int):
         query = delete(cls.model).where(cls.model.id == model_id)
         await session.execute(query)

     @classmethod
     async def find_one_or_none(cls, session: AsyncSession, **filter_by):
         query = select(cls.model).filter_by(**filter_by)
         result = await session.execute(query)
         return result.scalar_one_or_none()

     @classmethod
     async def find_all(cls, session: AsyncSession, **filter_by):
         query = select(cls.model).filter_by(**filter_by)
         result = await session.execute(query)
         return result.scalars().all()

     @classmethod
     async def update(cls, session: AsyncSession, model_id: int, **data):
         query = (update(cls.model).where(cls.model.id == model_id).values(**data))
         await session.execute(query)

     @classmethod
     async def update_by_slug(cls, session: AsyncSession, old_slug: str, **data):
         query = update(cls.model).where(cls.model.slug == old_slug).values(**data)
         await session.execute(query)

