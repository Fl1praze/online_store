from app.dao.base import BaseDAO
from app.products.models import Product
from app.database import async_session_maker
from sqlalchemy import select,and_

class ProductsDAO(BaseDAO):
    model = Product

    @classmethod
    async def get_active_stock_products(cls):
        async with async_session_maker() as session:
            query = select(cls.model).where(
                and_(cls.model.is_active==True, cls.model.stock>0)
            )
            result = await session.execute(query)
            return result.scalars().all()


    @classmethod
    async def find_by_category_ids(cls, category_ids: list[int]):
        async with async_session_maker() as session:
            query = select(cls.model).where(
                cls.model.category_id.in_(category_ids),
                cls.model.is_active == True,
                cls.model.stock > 0
            )
            result = await session.execute(query)
            return result.scalars().all()


