from app.dao.base import BaseDAO
from app.orders.models import Order,OrderItem
from app.database import async_session_maker
from sqlalchemy import insert

class OrderDAO(BaseDAO):
    model = Order

    @classmethod
    async def add_order(cls, **data):
        async with async_session_maker() as session:
            query = insert(cls.model).values(**data)
            result = await session.execute(query)
            await session.commit()

            new_id = result.inserted_primary_key[0]
            return new_id
class OrderItemDAO(BaseDAO):
    model = OrderItem
