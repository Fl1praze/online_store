"""
Функциональные тесты для API аутентификации.
Тестирование полного цикла работы API endpoints.
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
@patch('app.users.routers.send_verification_email_task.delay')
async def test_user_registration_flow(mock_celery_task, async_client: AsyncClient, db_session):
    """
    Функциональный тест: полный цикл регистрации пользователя.
    Тестирует POST /auth/register endpoint.
    """
    # Регистрируем нового пользователя
    registration_data = {
        "email": "newuser@test.com",
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "password": "securepassword123"
    }
    
    response = await async_client.post("/auth/register", json=registration_data)
    
    # Проверяем успешную регистрацию
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "successfully" in data["message"].lower() or "registered" in data["message"].lower()
    
    # Проверяем, что пользователь создан в БД
    from app.users.dao import UsersDAO
    user = await UsersDAO.find_one_or_none(db_session, email=registration_data["email"])
    assert user is not None
    assert user.email == registration_data["email"]
    assert user.username == registration_data["username"].capitalize()
    assert user.is_active == False  # Пользователь должен быть неактивен до подтверждения email

