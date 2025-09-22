

from app.dao.base import BaseDAO
from app.category.models import Category
from app.database import async_session_maker
from sqlalchemy import select


class CategoriesDAO(BaseDAO):
    model = Category

    @classmethod
    async def get_subcategories(cls, parent_id: int):
        async with async_session_maker() as session:
            query = select(cls.model.id).where(cls.model.parent_id == parent_id)
            result = await session.execute(query)
            return result.scalars().all()



