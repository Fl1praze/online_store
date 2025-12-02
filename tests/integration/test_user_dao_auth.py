"""
Интеграционные тесты для взаимодействия UsersDAO и auth модуля.
Тестирование работы компонентов вместе.
"""
import pytest
from app.users.dao import UsersDAO
from app.users.auth import get_password_hash, verify_password


@pytest.mark.asyncio
async def test_user_creation_and_password_verification(db_session):
    """
    Интеграционный тест: создание пользователя и проверка пароля.
    Тестирует взаимодействие UsersDAO и auth модуля.
    """
    # Создаём пользователя с хешированным паролем
    password = "testpassword123"
    hashed_password = get_password_hash(password)
    
    user_id = await UsersDAO.add(
        db_session,
        email="integration@test.com",
        username="integration_user",
        first_name="Integration",
        last_name="Test",
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False
    )
    await db_session.commit()
    
    # Получаем пользователя из БД
    user = await UsersDAO.find_by_id(db_session, user_id)
    assert user is not None
    assert user.email == "integration@test.com"
    
    # Проверяем, что пароль корректно сохранён и может быть проверен
    assert verify_password(password, user.hashed_password) is True
    assert verify_password("wrongpassword", user.hashed_password) is False

