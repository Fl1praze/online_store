"""
Unit тесты для создания JWT токенов (app/users/auth.py)
Тестирование функций создания токенов без зависимостей от БД.
"""
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.users.auth import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token
)
from app.config import settings


def test_create_access_token():
    """Unit тест: создание access токена"""
    user_id = 1
    password_version = 1
    token = create_access_token({"sub": str(user_id)}, password_version)
    
    # Токен не должен быть пустым
    assert token is not None
    assert len(token) > 0
    
    # Декодируем токен и проверяем содержимое
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["pwd_ver"] == password_version
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload
    
    # Проверяем, что срок действия около 30 минут
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_diff = exp_time - now
    assert timedelta(minutes=29) < time_diff < timedelta(minutes=31)


def test_create_refresh_token():
    """Unit тест: создание refresh токена"""
    user_id = 1
    password_version = 1
    token = create_refresh_token({"sub": str(user_id)}, password_version)
    
    # Токен не должен быть пустым
    assert token is not None
    
    # Декодируем токен и проверяем содержимое
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["pwd_ver"] == password_version
    
    # Проверяем, что срок действия больше чем у access токена (7 дней)
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_diff = exp_time - now
    assert time_diff > timedelta(days=6)  # Больше 6 дней


def test_create_email_verification_token():
    """Unit тест: создание токена для верификации email"""
    email = "test@example.com"
    token = create_email_verification_token(email)
    
    # Токен не должен быть пустым
    assert token is not None
    
    # Декодируем токен и проверяем содержимое
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == email
    assert payload["type"] == "email_verification"
    assert "exp" in payload
    
    # Проверяем, что срок действия около 24 часов
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_diff = exp_time - now
    assert timedelta(hours=23) < time_diff < timedelta(hours=25)

