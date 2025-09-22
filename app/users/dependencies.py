from datetime import datetime
from fastapi import Request, Depends, HTTPException,status
from jose import jwt,JWTError
from app.config import settings
from app.users.dao import UsersDAO


def get_token(request:Request):
    token = request.cookies.get('booking_access_token')
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='Token not found')
    return token


async def get_current_user(token:str = Depends(get_token)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
    except JWTError:
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,detail='Неверный формат токена')
    token_type = payload.get('type')
    if token_type != 'access':
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED,detail='Ожидался access token')
    expire:str = payload.get('exp')
    if (not expire) or (int(expire) < datetime.now().timestamp()):
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,detail='Токен истёк')
    user_id:str = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=401)
    user = await UsersDAO.find_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=401)
    pwd_hash_in_token = payload.get('pwd_hash')
    if not user.hashed_password.startswith(pwd_hash_in_token):
        raise HTTPException(status_code=401)
    return user