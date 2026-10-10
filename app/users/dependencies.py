from datetime import datetime
from fastapi import Request, Depends, HTTPException, status
from jose import jwt, JWTError
from app.config import settings
from app.users.dao import UsersDAO
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.users.models import Users



def get_token(request: Request):
    token = request.cookies.get('at')
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
    return token


async def get_current_user(
        token: str = Depends(get_token),
        session: AsyncSession = Depends(get_async_session)
) -> Users:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Неверный формат токена')

    token_type = payload.get('type')
    if token_type != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Ожидался access token')

    expire: str = payload.get('exp')

    if (not expire) or (int(expire) < datetime.now().timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен истёк')

    user_id: str = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await UsersDAO.find_by_id(session, int(user_id))

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    pwd_ver_token = payload.get('pwd_ver')
    if user.password_version != pwd_ver_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is outdated")

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error committing session in dependency: {e}")

    return user

