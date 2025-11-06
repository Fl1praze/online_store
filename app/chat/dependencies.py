from fastapi import Depends, HTTPException,status, Query

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.users.models import Users
from app.users.dao import UsersDAO

# Импортируем нашу новую функцию из auth.py
from app.users.auth import verify_websocket_token


async def get_user_from_ws_token(
        token: str = Query(..., description="Временный токен для WebSocket"),
        session: AsyncSession = Depends(get_async_session)
) -> Users:
    user_id = verify_websocket_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или просроченный токен WebSocket"
        )

    user = await UsersDAO.find_by_id(session, user_id)
    if not user:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сессии: {e}")

    return user

