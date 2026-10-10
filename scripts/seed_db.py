"""
Заполнение БД стартовыми данными: администратор, демо-пользователь,
категории (с подкатегориями) и товары.

Скрипт можно запускать повторно: существующие записи (по username / slug)
пропускаются, дубликаты не создаются.

Запуск из корня проекта (с активным .venv):
    python scripts/seed_db.py

Пароли можно задать через переменные окружения:
    SEED_ADMIN_PASSWORD, SEED_USER_PASSWORD
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path (как в остальных скриптах)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.users.auth import get_password_hash

# Импортируем все модели, чтобы SQLAlchemy знал обо всех таблицах (как в env.py)
from app.users.models import Users
from app.category.models import Category
from app.products.models import Product
from app.orders.models import Order, OrderItem  # noqa: F401
from app.cart.models import Cart, CartItem  # noqa: F401
from app.review.models import Review  # noqa: F401
from app.chat.models import ChatMessage  # noqa: F401


ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin12345!")
USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "User12345!")

USERS = [
    {
        "first_name": "Админ",
        "last_name": "Магазина",
        "username": "admin",
        "email": "admin@example.com",
        "password": ADMIN_PASSWORD,
        "is_admin": True,
    },
    {
        "first_name": "Иван",
        "last_name": "Покупатель",
        "username": "user",
        "email": "user@example.com",
        "password": USER_PASSWORD,
        "is_admin": False,
    },
]

# Родительская категория -> список подкатегорий
CATEGORIES = {
    "Смартфоны и гаджеты": ["Смартфоны", "Планшеты", "Умные часы"],
    "Ноутбуки и компьютеры": ["Ноутбуки", "Мониторы", "Комплектующие"],
    "ТВ и аудио": ["Телевизоры", "Наушники", "Портативные колонки"],
    "Бытовая техника": ["Холодильники", "Стиральные машины", "Пылесосы"],
}

# (подкатегория, название, цена в рублях, остаток на складе, рейтинг, описание)
PRODUCTS = [
    # Смартфоны
    ("Смартфоны", "Apple iPhone 15 128GB", 79990, 25, 4.8,
     "Смартфон с дисплеем Super Retina XDR 6.1 дюйма, чипом A16 Bionic и двойной камерой 48 Мп."),
    ("Смартфоны", "Samsung Galaxy S24 256GB", 74990, 18, 4.7,
     "Флагман на Exynos 2400 с экраном Dynamic AMOLED 2X 6.2 дюйма и функциями Galaxy AI."),
    ("Смартфоны", "Xiaomi Redmi Note 13 Pro 8/256GB", 27990, 40, 4.5,
     "AMOLED-экран 120 Гц, основная камера 200 Мп и быстрая зарядка 67 Вт."),
    ("Смартфоны", "Google Pixel 8 128GB", 59990, 10, 4.6,
     "Чистый Android, процессор Tensor G3 и семь лет обновлений."),
    # Планшеты
    ("Планшеты", "Apple iPad 10.9 (10-е поколение) 64GB", 39990, 15, 4.7,
     "Планшет с экраном Liquid Retina 10.9 дюйма, чипом A14 Bionic и поддержкой Apple Pencil."),
    ("Планшеты", "Samsung Galaxy Tab S9 FE 128GB", 36990, 12, 4.4,
     "Экран 10.9 дюйма 90 Гц, защита IP68 и стилус S Pen в комплекте."),
    ("Планшеты", "Xiaomi Pad 6 8/256GB", 29990, 20, 4.5,
     "Экран 11 дюймов 144 Гц, процессор Snapdragon 870 и четыре динамика."),
    # Умные часы
    ("Умные часы", "Apple Watch Series 9 45 мм", 42990, 14, 4.8,
     "Яркий дисплей Always-On, датчики ЭКГ и кислорода в крови, жест двойного касания."),
    ("Умные часы", "Samsung Galaxy Watch6 44 мм", 24990, 16, 4.5,
     "Мониторинг сна и состава тела, AMOLED-экран и до 40 часов автономной работы."),
    ("Умные часы", "Xiaomi Watch S3", 11990, 30, 4.3,
     "Сменные безели, экран AMOLED 1.43 дюйма и до 15 дней работы от одной зарядки."),
    # Ноутбуки
    ("Ноутбуки", "Apple MacBook Air 13 M2 8/256GB", 99990, 9, 4.9,
     "Тонкий безвентиляторный ноутбук на чипе M2 с дисплеем Liquid Retina 13.6 дюйма."),
    ("Ноутбуки", "ASUS Vivobook 15 OLED 16/512GB", 54990, 13, 4.4,
     "OLED-экран 15.6 дюйма Full HD, процессор Intel Core i5 и быстрый SSD NVMe."),
    ("Ноутбуки", "Lenovo IdeaPad Gaming 3 16/512GB", 69990, 8, 4.5,
     "Игровой ноутбук с видеокартой GeForce RTX 3050 и экраном 15.6 дюйма 120 Гц."),
    ("Ноутбуки", "HP Pavilion 15 16/512GB", 49990, 11, 4.3,
     "Универсальный ноутбук для учёбы и работы: Ryzen 5, SSD 512 ГБ, FHD IPS."),
    # Мониторы
    ("Мониторы", "LG UltraGear 27GP850-B 27\"", 32990, 17, 4.7,
     "Игровой монитор Nano IPS 27 дюймов, QHD, 165 Гц, время отклика 1 мс."),
    ("Мониторы", "Samsung Odyssey G5 32\"", 28990, 10, 4.5,
     "Изогнутый VA-монитор 32 дюйма, QHD, 144 Гц, поддержка FreeSync Premium."),
    ("Мониторы", "Dell S2722QC 27\" 4K", 31990, 7, 4.6,
     "4K IPS-монитор с USB-C, подходит для работы и мультимедиа."),
    # Комплектующие
    ("Комплектующие", "Samsung 980 PRO SSD 1TB", 11990, 35, 4.8,
     "Накопитель NVMe PCIe 4.0 со скоростью чтения до 7000 МБ/с."),
    ("Комплектующие", "Kingston Fury Beast DDR5 32GB (2x16GB) 5600MHz", 9990, 28, 4.6,
     "Комплект оперативной памяти DDR5 для современных платформ Intel и AMD."),
    # Телевизоры
    ("Телевизоры", "Samsung UE55CU8000 55\" 4K", 49990, 12, 4.6,
     "Смарт-телевизор 55 дюймов, Crystal 4K, Tizen, поддержка HDR10+."),
    ("Телевизоры", "LG 50UR78009LL 50\" 4K", 38990, 15, 4.4,
     "4K-телевизор на webOS с процессором α5 Gen6 и голосовым управлением."),
    ("Телевизоры", "Xiaomi TV A Pro 55\" 4K", 32990, 20, 4.3,
     "Телевизор 55 дюймов с Google TV, Dolby Vision и тонким корпусом."),
    # Наушники
    ("Наушники", "Apple AirPods Pro 2 (USB-C)", 21990, 30, 4.8,
     "Беспроводные наушники с активным шумоподавлением и адаптивным звуком."),
    ("Наушники", "Sony WH-1000XM5", 29990, 14, 4.8,
     "Полноразмерные наушники с лучшим в классе шумоподавлением и автономностью до 30 часов."),
    ("Наушники", "JBL Tune 520BT", 3990, 50, 4.3,
     "Накладные Bluetooth-наушники с басами JBL Pure Bass и работой до 57 часов."),
    # Колонки
    ("Портативные колонки", "JBL Flip 6", 9990, 25, 4.7,
     "Портативная колонка с защитой IP67, мощным звуком и автономностью до 12 часов."),
    ("Портативные колонки", "Yandex Станция Мини", 7490, 22, 4.4,
     "Умная колонка с голосовым помощником Алисой и часами на корпусе."),
    # Холодильники
    ("Холодильники", "Bosch Serie 4 KGN39VL25R", 64990, 6, 4.6,
     "Двухкамерный холодильник NoFrost, объём 366 литров, класс энергопотребления E."),
    ("Холодильники", "Haier C2F637CXRG", 59990, 5, 4.5,
     "Холодильник 364 литра с системой Total No Frost и внутренним LED-освещением."),
    # Стиральные машины
    ("Стиральные машины", "LG F2V3WS6SS", 38990, 9, 4.6,
     "Стиральная машина с загрузкой 6.5 кг, технологией AI DD и паровой обработкой."),
    ("Стиральные машины", "Samsung WW70AA626AX", 34990, 11, 4.5,
     "Машина 7 кг с инверторным мотором Digital Inverter и функцией Eco Bubble."),
    # Пылесосы
    ("Пылесосы", "Dyson V12 Detect Slim", 59990, 8, 4.8,
     "Беспроводной пылесос с лазерной подсветкой пыли и автономной работой до 60 минут."),
    ("Пылесосы", "Xiaomi Robot Vacuum S10", 22990, 14, 4.4,
     "Робот-пылесос с лидарной навигацией, влажной уборкой и управлением через приложение."),
]


async def get_or_create_user(session: AsyncSession, data: dict) -> bool:
    exists = await session.scalar(select(Users).where(Users.username == data["username"]))
    if exists:
        return False
    session.add(Users(
        first_name=data["first_name"],
        last_name=data["last_name"],
        username=data["username"],
        email=data["email"],
        hashed_password=get_password_hash(data["password"]),
        is_active=True,   # без подтверждения email
        is_admin=data["is_admin"],
        password_version=1,
    ))
    return True


async def get_or_create_category(session: AsyncSession, name: str, parent_id: int | None = None) -> tuple[Category, bool]:
    slug = slugify(name)
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category:
        return category, False
    category = Category(name=name, slug=slug, is_active=True, parent_id=parent_id)
    session.add(category)
    await session.flush()  # чтобы получить id
    return category, True


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"БД: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    async with session_factory() as session:
        # Пользователи
        users_added = 0
        for user in USERS:
            if await get_or_create_user(session, user):
                users_added += 1
        await session.flush()

        # Категории
        categories_added = 0
        sub_by_name: dict[str, Category] = {}
        for parent_name, children in CATEGORIES.items():
            parent, created = await get_or_create_category(session, parent_name)
            categories_added += created
            for child_name in children:
                child, created = await get_or_create_category(session, child_name, parent.id)
                categories_added += created
                sub_by_name[child_name] = child

        # Товары
        products_added = 0
        for category_name, name, price, stock, rating, description in PRODUCTS:
            slug = slugify(name)
            exists = await session.scalar(select(Product).where(Product.slug == slug))
            if exists:
                continue
            session.add(Product(
                name=name,
                slug=slug,
                description=description,
                price=price,
                stock=stock,
                rating=rating,
                is_active=True,
                category_id=sub_by_name[category_name].id,
                # Имена файлов по той же схеме, что в app/products/routers.py
                small_image=f"{slug}_small.jpg",
                large_image=f"{slug}_large.jpg",
            ))
            products_added += 1

        await session.commit()

    await engine.dispose()

    print("\nГотово.")
    print(f"  Пользователей добавлено: {users_added}")
    print(f"  Категорий добавлено:     {categories_added}")
    print(f"  Товаров добавлено:       {products_added}")
    if users_added:
        print("\nДоступы (смените пароли после первого входа):")
        print(f"  admin / {ADMIN_PASSWORD}")
        print(f"  user  / {USER_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())