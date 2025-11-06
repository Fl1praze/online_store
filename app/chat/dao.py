from app.dao.base import BaseDAO # Используем наш базовый DAO
from app.chat.models import ChatMessage # Импортируем новую модель
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc # Добавляем desc для сортировки

class ChatMessageDAO(BaseDAO):
    model = ChatMessage

    @classmethod
    async def get_last_n_messages(cls, session: AsyncSession, n: int = 50):
        """
        Получает последние N сообщений из чата, отсортированные по времени (сначала старые).
        (Пока не учитываем recipient_id, просто общая история)
        """
        query = (
            select(cls.model)
            .order_by(desc(cls.model.timestamp)) # Сначала сортируем по убыванию (новые вверху)
            .limit(n) # Берем N последних
        )
        result = await session.execute(query)
        messages = result.scalars().all()
        return messages[::-1] # Разворачиваем список

    @classmethod
    async def get_history_for_client(cls, session: AsyncSession, client_id: int, n: int = 50):
        """
        Получает последние N сообщений для конкретного клиента
        (от него админам или от админов ему).
        """
        query = (
            select(cls.model)
            .where(
                (cls.model.sender_id == client_id) |
                (cls.model.recipient_id == client_id)
            )
            .order_by(desc(cls.model.timestamp))
            .limit(n)
        )
        result = await session.execute(query)
        messages = result.scalars().all()
        return messages[::-1]
