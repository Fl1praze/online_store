"""
Конфигурация и фикстуры для тестов
"""
import os
import sys
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Устанавливаем переменные окружения ДО импорта любых модулей
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("EMAIL_SENDER", "test@test.com")
os.environ.setdefault("SMTP_HOST", "smtp.test.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")

# Импортируем config и переопределяем DATABASE_URL
import app.config as config_module

# Убеждаемся, что DATABASE_URL установлен на SQLite
if not config_module.settings.DATABASE_URL.startswith('sqlite'):
    config_module.settings.DATABASE_URL = 'sqlite+aiosqlite:///:memory:'

# Импортируем Base из database (используем его для моделей)
# Если импорт не удался из-за asyncpg, используем свой Base
try:
    from app.database import Base
    from app.database import get_async_session
except (ImportError, ModuleNotFoundError) as e:
    # Если не удалось импортировать из-за отсутствия asyncpg, создаём свой Base
    from sqlalchemy.orm import DeclarativeBase
    Base = DeclarativeBase()
    # Создаём заглушку для get_async_session
    async def get_async_session():
        yield None

# Импортируем main app
# Если не удалось импортировать из-за отсутствующих зависимостей, создаём минимальное тестовое приложение
try:
    from main import app
except Exception as e:
    print(f"Warning: Could not import main app: {e}")
    from fastapi import FastAPI
    app = FastAPI()
    # Добавляем роутеры для тестов
    try:
        from app.users.routers import router as users_routers
        app.include_router(users_routers)
    except Exception as router_error:
        print(f"Warning: Could not import users router: {router_error}")
    try:
        from app.products.routers import router as products_routers
        app.include_router(products_routers)
    except Exception as router_error:
        print(f"Warning: Could not import products router: {router_error}")

# Тестовая база данных в памяти
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Создаём тестовый движок
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Переопределение зависимости для тестовой БД"""
    async with TestSessionLocal() as session:
        yield session


# Переопределяем зависимость
app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Фикстура для создания тестовой сессии БД.
    Создаёт таблицы перед тестом и удаляет после.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Фикстура для создания асинхронного HTTP клиента для тестирования API.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def sync_client() -> TestClient:
    """
    Фикстура для создания синхронного HTTP клиента для тестирования API.
    """
    return TestClient(app)


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    """
    Фикстура для создания тестового пользователя.
    """
    from app.users.dao import UsersDAO
    from app.users.auth import get_password_hash
    
    user_id = await UsersDAO.add(
        db_session,
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_admin=False
    )
    await db_session.commit()
    
    user = await UsersDAO.find_by_id(db_session, user_id)
    return user


@pytest.fixture(scope="function")
async def test_admin_user(db_session: AsyncSession):
    """
    Фикстура для создания тестового администратора.
    """
    from app.users.dao import UsersDAO
    from app.users.auth import get_password_hash
    
    user_id = await UsersDAO.add(
        db_session,
        email="admin@example.com",
        username="admin",
        first_name="Admin",
        last_name="User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_admin=True
    )
    await db_session.commit()
    
    user = await UsersDAO.find_by_id(db_session, user_id)
    return user


@pytest.fixture(scope="function")
async def test_category(db_session: AsyncSession):
    """
    Фикстура для создания тестовой категории.
    """
    from app.category.dao import CategoriesDAO
    
    category_id = await CategoriesDAO.add(
        db_session,
        name="Тестовая категория",
        slug="test-category",
        is_active=True
    )
    await db_session.commit()
    
    category = await CategoriesDAO.find_by_id(db_session, category_id)
    return category


@pytest.fixture(scope="function")
async def test_product(db_session: AsyncSession, test_category):
    """
    Фикстура для создания тестового товара.
    """
    from app.products.dao import ProductsDAO
    
    product_id = await ProductsDAO.add(
        db_session,
        name="Тестовый товар",
        slug="test-product",
        description="Описание тестового товара",
        price=1000,
        stock=10,
        category_id=test_category.id,
        is_active=True,
        small_image="test_small.jpg",
        large_image="test_large.jpg"
    )
    await db_session.commit()
    
    product = await ProductsDAO.find_by_id(db_session, product_id)
    return product


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """
    Фикстура для создания заголовков авторизации.
    """
    from app.users.auth import create_access_token
    
    token = create_access_token({"sub": str(test_user.id)}, test_user.password_version)
    return {"Cookie": f"booking_access_token={token}"}

