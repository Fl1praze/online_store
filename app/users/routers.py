from fastapi import APIRouter, Response, Depends, HTTPException,status,Request
from jose import jwt,JWTError
from app.users.auth import get_password_hash, verify_password, create_access_token,create_refresh_token
from app.users.dao import UsersDAO
from app.users.schemas import CreateUser,LoginUser
from app.users.models import Users
from app.users.dependencies import get_current_user
from app.config import settings
router = APIRouter(prefix='/auth',tags =['Auth & Users '])


#Выйти со всех устройств
#Изменить данные о пользователе
#OAuth 2 google

@router.post('/register')
async def register_user(user_data:CreateUser):
    try_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if try_user:
        raise HTTPException( status_code = status.HTTP_409_CONFLICT,detail='Пользователь уже существует')
    try_username = await UsersDAO.find_one_or_none(username=user_data.username)
    if try_username:
        raise HTTPException( status_code= status.HTTP_409_CONFLICT,detail='Имя пользователя занято')
    hashed_password = get_password_hash(user_data.password)
    await UsersDAO.add(
        email = user_data.email,
        hashed_password=hashed_password,
        first_name = user_data.first_name,
        last_name = user_data.last_name,
        username = user_data.username
    )
    return {"message": "User registered successfully"}


@router.post('/login')
async def login_user(response: Response,user_data:LoginUser):
    user = await UsersDAO.find_one_or_none(email=user_data.email)
    if not user:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,detail='Пользователя с данной почтой не существует')
    if user:
        password_is_valid = verify_password(user_data.password, user.hashed_password)
        if not password_is_valid:
            raise HTTPException(status_code = status.HTTP_409_CONFLICT,detail='Неверный пароль')
    access_token =  create_access_token({"sub":str(user.id)},user.hashed_password)
    refresh_token = create_access_token({"sub":str(user.id)},user.hashed_password)
    #ИСправить название токена
    response.set_cookie('booking_access_token', access_token, httponly=True, max_age=1800,secure=True,samesite="lax")
    response.set_cookie('booking_refresh_token', refresh_token, httponly=True, max_age=604800,secure=True,samesite="lax")
    return {'message':'user login success'}


@router.post('/logout')
async def logout_user(response:Response):
    response.delete_cookie('booking_access_token')
    response.delete_cookie('booking_refresh_token')
    return {'message':'user logout success'}


@router.get('/me')
async def read_user_me(current_user:Users =Depends(get_current_user)):
    return current_user


@router.put('/change_pwd')
async def change_password(old_pwd:str,new_pwd: str,current_user:Users =Depends(get_current_user)):
    old_pwd_chek = verify_password(old_pwd,current_user.hashed_password)
    if not old_pwd_chek:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail='Неверный пароль')
    new_pwd_hash = get_password_hash(new_pwd)
    await UsersDAO.update(current_user.id,hashed_password=new_pwd_hash)
    return {'message':'password update successful'}


@router.post('refresh')
async def refresh_token(request: Request, response: Response):
    refresh_token = request.cookies.get('booking_refresh_token')
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token отсутствует')
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        pwd_hash_in_token = payload.get("pwd_hash")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')

    user = await UsersDAO.find_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не найден')

    if not user.hashed_password.startswith(pwd_hash_in_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Refresh token недействителен (пароль изменён)')

    new_access_token = create_access_token({"sub": str(user.id)}, user.hashed_password)
    new_refresh_token = create_refresh_token({"sub": str(user.id)}, user.hashed_password)

    response.set_cookie('booking_access_token', new_access_token, httponly=True, max_age=1800)
    response.set_cookie('booking_refresh_token', new_refresh_token, httponly=True, max_age=604800)

    return {
        "message": "Token refreshed",
        "access_token": new_access_token,
        "token_type": "bearer"
    }


