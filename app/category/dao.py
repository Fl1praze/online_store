from app.dao.base import BaseDAO
from app.category.models import Category

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class CategoriesDAO(BaseDAO):
    model = Category

    @classmethod
    async def get_subcategories(cls, session: AsyncSession, parent_id: int):
        query = select(cls.model.id).where(cls.model.parent_id == parent_id)
        result = await session.execute(query)
        return result.scalars().all()



