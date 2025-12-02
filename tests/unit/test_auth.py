"""
Unit тесты для модуля аутентификации (app/users/auth.py)
Тестирование отдельных функций без зависимостей от БД.
"""
from app.users.auth import get_password_hash, verify_password


def test_password_hashing_and_verification():
    """Unit тест: хеширование и проверка пароля"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    # Хеш не должен быть пустым
    assert hashed is not None
    assert len(hashed) > 0
    # Хеш не должен совпадать с оригинальным паролем
    assert hashed != password
    # Хеш должен начинаться с $argon2 (формат argon2)
    assert hashed.startswith("$argon2")
    
    # Правильный пароль должен проходить проверку
    assert verify_password(password, hashed) is True
    
    # Неправильный пароль не должен проходить проверку
    wrong_password = "wrongpassword"
    assert verify_password(wrong_password, hashed) is False



