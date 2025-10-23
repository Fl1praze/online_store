from app.dao.base import BaseDAO
from app.orders.models import Order,OrderItem
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

class OrderDAO(BaseDAO):
    model = Order

    @classmethod
    async def add_order(cls, session: AsyncSession, **data):
        query = insert(cls.model).values(**data)
        result = await session.execute(query)
        await session.flush()
        new_id = result.inserted_primary_key[0]
        return new_id


class OrderItemDAO(BaseDAO):
    model = OrderItem
