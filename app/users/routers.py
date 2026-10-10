import json
from fastapi import APIRouter, Response, Depends, HTTPException,status,Request
from fastapi.responses import RedirectResponse
from jose import jwt,JWTError
from sqlalchemy.exc import IntegrityError
from app.users.auth import get_password_hash, verify_password, create_at,create_rf,create_email_verification_token
from app.users.dao import UsersDAO
from app.users.schemas import CreateUser,LoginUser,ChangePasswordRequest,ChangeData,UserResponse,AdminUpdateUser
from app.users.models import Users
from app.users.dependencies import get_current_user
from app.config import settings
from app.tasks import send_verification_email_task
from app.redis_client import redis_client
from app.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.rate_limiter import limiter, REGISTER_LIMIT, LOGIN_LIMIT

router = APIRouter(prefix='/auth',tags =['Auth & Users '])


@router.post('/register')
@limiter.limit(REGISTER_LIMIT)
async def register_user(
        request: Request,
        user_data: CreateUser,
        session: AsyncSession = Depends(get_async_session)
):
    # Нормализуем данные перед проверкой
    normalized_username = user_data.username.capitalize()
    normalized_first_name = user_data.first_name.capitalize()
    normalized_last_name = user_data.last_name.capitalize()
    
    async with session.begin():
        try_user = await UsersDAO.find_one_or_none(session, email=user_data.email)
        if try_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Пользователь c такой почтой  существует')
        
        # Проверяем username с учётом нормализации
        try_username = await UsersDAO.find_one_or_none(session, username=normalized_username)
        if try_username:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Имя пользователя занято')

        hashed_password = get_password_hash(user_data.password)
        
        try:
            await UsersDAO.add(
                session,  # Передали сессию
                email=user_data.email,
                hashed_password=hashed_password,
                first_name=normalized_first_name,
                last_name=normalized_last_name,
                username=normalized_username
            )
        except IntegrityError as e:
            # Обрабатываем ошибки уникальности (race condition или другие проблемы)
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            if "username" in error_str.lower() or "users_username_key" in error_str.lower():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Имя пользователя занято')
            elif "email" in error_str.lower() or "users_email_key" in error_str.lower():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Пользователь c такой почтой  существует')
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Пользователь с такими данными уже существует')
        except Exception as e:
            # Обрабатываем другие ошибки
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка при регистрации. Попробуйте позже.')

    token = create_email_verification_token(user_data.email)
    send_verification_email_task.delay(user_data.email, token)
    return {"message": "User registered successfully"}


@router.get("/verify-email")
async def verify_email(
        token: str,
        session: AsyncSession = Depends(get_async_session)
):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        email = payload.get("sub")

        if token_type != "email_verification":
            # Редирект на главную с сообщением об ошибке
            return RedirectResponse(url="/?error=invalid_token", status_code=302)
        if not email:
            return RedirectResponse(url="/?error=invalid_token", status_code=302)
    except JWTError:
        # Редирект на главную с сообщением об ошибке
        return RedirectResponse(url="/?error=expired_token", status_code=302)

    async with session.begin():
        user = await UsersDAO.find_one_or_none(session, email=email)
        if not user:
            return RedirectResponse(url="/?error=user_not_found", status_code=302)
        await UsersDAO.update(session, user.id, is_active=True)

    # Успешное подтверждение - редирект на главную с сообщением об успехе
    return RedirectResponse(url="/?success=email_verified", status_code=302)


@router.post('/login')
@limiter.limit(LOGIN_LIMIT)
async def login_user(
        request: Request,
        response: Response,
        user_data: LoginUser,
        session: AsyncSession = Depends(get_async_session)
):
    user = await UsersDAO.find_one_or_none(session, email=user_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Пользователя с данной почтой не существует')
    if user:
        password_is_valid = verify_password(user_data.password, user.hashed_password)
        if not password_is_valid:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Неверный пароль')
    user_verif_email = user.is_active
    if not user_verif_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='email не подтвержден')

    at = create_at({"sub": str(user.id)}, user.password_version)
    rf = create_rf({"sub": str(user.id)}, user.password_version)
    response.set_cookie('at', at, httponly=True, max_age=1800, secure=True, samesite="lax")
    response.set_cookie('rf', rf, httponly=True, max_age=604800, secure=True,
                        samesite="lax")
    return {'message': 'user login success'}


@router.post('/logout')
async def logout_user(response: Response):
    response.delete_cookie('at')
    response.delete_cookie('rf')
    return {'message': 'user logout success'}


@router.get('/me')
async def read_user_me(
        current_user: Users = Depends(get_current_user),
):
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
    redis_client.setex(cache_key, 600, json.dumps(data_list))
    return current_user


@router.put('/change_pwd')
async def change_password(
        request: ChangePasswordRequest,
        response: Response,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    old_pwd_chek = verify_password(request.old_password, current_user.hashed_password)
    if not old_pwd_chek:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Неверный пароль')

    async with session.begin():
        new_version_token = await UsersDAO.rotate_password_version(session, current_user.id)
        if new_version_token is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        new_pwd_hash = get_password_hash(request.new_password)
        await UsersDAO.update(session, current_user.id, hashed_password=new_pwd_hash)

    new_at = create_at({"sub": str(current_user.id)}, new_version_token)
    response.set_cookie('at', new_at, httponly=True, max_age=1800)

    redis_client.delete(f'user:{current_user.id}')
    return {'message': 'password update successful'}


@router.put('/change_data')
async def change_data(
        data: ChangeData,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        await UsersDAO.update(
            session,
            current_user.id,
            first_name=data.first_name.capitalize(),
            last_name=data.last_name.capitalize(),
            username=data.username.capitalize()
        )

    redis_client.delete(f'user:{current_user.id}')
    return {'message': 'update successful'}


@router.post('/logout_other_sessions')
async def logout_other_sessions(
        responce: Response,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        new_version = await UsersDAO.rotate_password_version(session, current_user.id)
        if new_version is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    new_at = create_at({"sub": str(current_user.id)}, password_version=new_version)
    responce.set_cookie('at', new_at, httponly=True, max_age=1800)
    return {
        "message": "Все другие сеансы успешно завершены",
        "new_password_version": new_version
    }


@router.post('/refresh')
async def refresh_token(
        request: Request,
        response: Response,
        session: AsyncSession = Depends(get_async_session)
):
    rf = request.cookies.get('rf')
    if not rf:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token отсутствует')

    try:
        payload = jwt.decode(rf, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        pwd_ver_in_token: int = payload.get("pwd_ver")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Невалидный refresh token')

    user = await UsersDAO.find_by_id(session, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не найден')

    if user.password_version != pwd_ver_in_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token недействителен")

    new_at = create_at({"sub": str(user.id)}, user.password_version)
    new_rf = create_rf({"sub": str(user.id)}, user.password_version)

    response.set_cookie('at', new_at, httponly=True, max_age=1800, secure=True, samesite="lax")
    response.set_cookie('rf', new_rf, httponly=True, max_age=604800, secure=True, samesite="lax")

    return {
        "message": "Token refreshed",
        "at": new_at,
        "token_type": "bearer"
    }


# Эндпоинты для админки
@router.get("/admin/users", response_model=list[UserResponse])
async def get_all_users(
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Доступ запрещён')
    
    try:
        users = await UsersDAO.find_all(session)
        return users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Ошибка получения пользователей: {str(e)}')


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
        user_id: int,
        user_data: AdminUpdateUser,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Доступ запрещён')
    
    user = await UsersDAO.find_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Пользователь не найден')
    
    # Подготавливаем данные для обновления
    update_data = {}
    
    if user_data.first_name is not None:
        update_data['first_name'] = user_data.first_name.capitalize() if user_data.first_name else None
    if user_data.last_name is not None:
        update_data['last_name'] = user_data.last_name.capitalize() if user_data.last_name else None
    if user_data.username is not None:
        normalized_username = user_data.username.capitalize() if user_data.username else None
        # Проверяем уникальность username, если он изменяется
        if normalized_username != user.username:
            existing_user = await UsersDAO.find_one_or_none(session, username=normalized_username)
            if existing_user:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Имя пользователя занято')
        update_data['username'] = normalized_username
    if user_data.email is not None:
        # Проверяем уникальность email, если он изменяется
        if user_data.email != user.email:
            existing_user = await UsersDAO.find_one_or_none(session, email=user_data.email)
            if existing_user:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email уже используется')
        update_data['email'] = user_data.email
    if user_data.is_active is not None:
        update_data['is_active'] = user_data.is_active
    if user_data.is_admin is not None:
        update_data['is_admin'] = user_data.is_admin
    
    try:
        await UsersDAO.update(session, user_id, **update_data)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        if "username" in error_str.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Имя пользователя занято')
        elif "email" in error_str.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email уже используется')
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Ошибка обновления данных')
    
    updated_user = await UsersDAO.find_by_id(session, user_id)
    return updated_user

