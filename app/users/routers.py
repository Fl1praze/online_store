import json

from fastapi import APIRouter, Response, Depends, HTTPException,status,Request
from jose import jwt,JWTError
from app.users.auth import get_password_hash, verify_password, create_access_token,create_refresh_token,create_email_verification_token
from app.users.dao import UsersDAO
from app.users.schemas import CreateUser,LoginUser,ChangePasswordRequest,ChangeData
from app.users.models import Users
from app.users.dependencies import get_current_user
from app.config import settings
from app.tasks import send_verification_email_task
from app.redis_client import redis_client

router = APIRouter(prefix='/auth',tags =['Auth & Users '])


@router.post('/register')
async def register_user(user_data:CreateUser,):
    try_user = await UsersDAO.find_one_or_none(email=user_data.email)
    if try_user:
        raise HTTPException( status_code = status.HTTP_409_CONFLICT,detail='Пользователь c такой почтой  существует')
    try_username = await UsersDAO.find_one_or_none(username=user_data.username)
    if try_username:
        raise HTTPException( status_code= status.HTTP_409_CONFLICT,detail='Имя пользователя занято')
    hashed_password = get_password_hash(user_data.password)
    await UsersDAO.add(
        email = user_data.email,
        hashed_password=hashed_password,
        first_name = user_data.first_name.capitalize(),
        last_name = user_data.last_name.capitalize(),
        username = user_data.username.capitalize()
    )
    token = create_email_verification_token(user_data.email)
    send_verification_email_task.delay(user_data.email,token)
    return {"message": "User registered successfully"}


@router.get("/verify-email")
async def verify_email(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        email = payload.get("sub")

        if token_type != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await UsersDAO.find_one_or_none(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await UsersDAO.update(user.id, is_active=True)
    return {"message": "Email успешно подтверждён!"}



@router.post('/login')
async def login_user(response: Response,user_data:LoginUser):
    user = await UsersDAO.find_one_or_none(email=user_data.email)
    if not user:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,detail='Пользователя с данной почтой не существует')
    if user:
        password_is_valid = verify_password(user_data.password, user.hashed_password)
        if not password_is_valid:
            raise HTTPException(status_code = status.HTTP_409_CONFLICT,detail='Неверный пароль')
    user_verif_email = user.is_active
    if not user_verif_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='email не подтвержден')
    access_token =  create_access_token({"sub":str(user.id)},user.password_version)
    refresh_token = create_refresh_token({"sub":str(user.id)},user.password_version)
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
    cache_key = f'user:{current_user.id}'
    cache_value = redis_client.get(cache_key)

    if cache_value:
        return json.loads(cache_value)
    data_list = {
        'id': current_user.id,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'username': current_user.username,
        'email': current_user.email
    }
    redis_client.setex(cache_key,600,json.dumps(data_list))

    return current_user


@router.put('/change_pwd')
async def change_password(request: ChangePasswordRequest ,response: Response,current_user:Users =Depends(get_current_user)):
    old_pwd_chek = verify_password(request.old_password,current_user.hashed_password)
    if not old_pwd_chek:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail='Неверный пароль')
    new_version_token = await UsersDAO.rotate_password_version(current_user.id)
    if new_version_token is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    new_pwd_hash = get_password_hash(request.new_password)
    await UsersDAO.update(current_user.id,hashed_password=new_pwd_hash,password_version=new_version_token)
    new_access_token = create_access_token({"sub": str(current_user.id)},new_version_token)
    response.set_cookie('booking_access_token', new_access_token, httponly=True, max_age=1800)

    redis_client.delete(f'user:{current_user.id}')
    return {'message':'password update successful'}


@router.put('/change_data')
async def change_data(data:ChangeData,current_user : Users = Depends(get_current_user)):
    await UsersDAO.update(current_user.id,first_name=data.first_name.capitalize(),last_name=data.last_name.capitalize(),username=data.username.capitalize())
    redis_client.delete(f'user:{current_user.id}')
    return {'message':'update successful'}



@router.post('/logout_other_sessions')
async def logout_other_sessions(responce: Response,current_user: Users = Depends(get_current_user)):
    new_version = await UsersDAO.rotate_password_version(current_user.id)
    if new_version is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    new_access_token = create_access_token({"sub": str(current_user.id)},password_version=new_version)
    responce.set_cookie('booking_access_token',new_access_token,httponly=True,max_age=1800)
    return {
        "message": "Все другие сеансы успешно завершены",
        "new_password_version": new_version
    }


@router.post('refresh')
async def refresh_token(request: Request, response: Response):
    refresh_token = request.cookies.get('booking_refresh_token')
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token отсутствует')
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        pwd_ver_in_token: int = payload.get("pwd_ver")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')

    user = await UsersDAO.find_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не найден')

    if user.password_version != pwd_ver_in_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token недействителен")

    new_access_token = create_access_token({"sub": str(user.id)}, user.password_version)
    new_refresh_token = create_refresh_token({"sub": str(user.id)}, user.password_version)

    response.set_cookie('booking_access_token', new_access_token, httponly=True, max_age=1800)
    response.set_cookie('booking_refresh_token', new_refresh_token, httponly=True, max_age=604800)

    return {
        "message": "Token refreshed",
        "access_token": new_access_token,
        "token_type": "bearer"
    }



