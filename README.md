# 🛒 Интернет-магазин на FastAPI

Полнофункциональный интернет-магазин с админ-панелью, построенный на FastAPI с использованием PostgreSQL, Redis, Celery и WebSocket.

## ✨ Основные возможности

### Для пользователей
- 🔐 **Аутентификация и авторизация**
  - Регистрация с подтверждением email
  - JWT токены (access + refresh)
  - Восстановление пароля
  - Смена данных профиля

- 🛍️ **Каталог товаров**
  - Просмотр товаров с фильтрацией
  - Поиск по названию
  - Фильтрация по категориям, цене, наличию
  - Пагинация
  - Детальная страница товара

- 🛒 **Корзина и заказы**
  - Добавление товаров в корзину
  - Управление количеством
  - Оформление заказов
  - История заказов
  - Отмена заказов (pending/processing)

- ⭐ **Отзывы и рейтинги**
  - Оставление отзывов на товары
  - Рейтинговая система
  - Просмотр отзывов других пользователей

- 💬 **Онлайн-чат**
  - WebSocket чат в реальном времени
  - Общение с другими пользователями

### Для администраторов
- 📊 **Админ-панель**
  - Управление товарами (создание, редактирование, удаление)
  - Управление категориями
  - Управление заказами
  - Управление пользователями
  - Просмотр и модерация отзывов
  - Статистика и аналитика

### Безопасность
- 🛡️ **Rate Limiting** (защита от атак)
  - Логин: 5 попыток в минуту
  - Регистрация: 3 регистрации в час
  - Создание заказов: 10 заказов в минуту
  - Добавление в корзину: 30 добавлений в минуту
  - Поиск: 60 запросов в минуту

- 🔒 **Безопасность**
  - Хеширование паролей (Argon2)
  - JWT токены с версионированием паролей
  - Email верификация
  - Защита от CSRF

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker и Docker Compose (опционально)

### Установка

1. **Клонируйте репозиторий**
```bash
git clone <repository-url>
cd NewFastAPI
```

2. **Создайте виртуальное окружение**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости**
```bash
pip install -r requirements.txt
```

4. **Настройте переменные окружения**

Создайте файл `.env` в корне проекта:
```env
# База данных
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your_password
DB_NAME=online_store

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Email (для верификации)
EMAIL_SENDER=noreply@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

5. **Создайте базу данных**
```bash
createdb online_store
```

6. **Примените миграции**
```bash
alembic upgrade head
```

7. **Запустите Redis** (если не используете Docker)
```bash
redis-server
```

8. **Запустите Celery worker** (в отдельном терминале)
```bash
celery -A app.celery_app worker --loglevel=info
```

9. **Запустите приложение**
```bash
uvicorn main:app --reload
```

Приложение будет доступно по адресу: `http://localhost:8000`

## 🐳 Запуск через Docker

1. **Создайте `.env` файл** (см. выше)

2. **Запустите все сервисы**
```bash
docker-compose up -d --build
```

Сервисы будут доступны:
- Web: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

3. **Примените миграции**
```bash
docker-compose exec web alembic upgrade head
```

4. **Остановка**
```bash
docker-compose down
```

## 📁 Структура проекта

```
NewFastAPI/
├── app/
│   ├── admin/          # Админ-панель
│   ├── cart/           # Корзина
│   ├── category/       # Категории
│   ├── chat/           # WebSocket чат
│   ├── orders/         # Заказы
│   ├── products/       # Товары
│   ├── review/         # Отзывы
│   ├── security/       # Rate limiting
│   ├── shop/           # Публичный фронт
│   ├── users/          # Пользователи и аутентификация
│   ├── config.py       # Конфигурация
│   ├── database.py     # Подключение к БД
│   ├── celery_app.py   # Celery конфигурация
│   └── tasks.py        # Фоновые задачи
├── scripts/            # Вспомогательные скрипты
├── static/             # Статические файлы (изображения)
├── templates/          # HTML шаблоны
├── tests/              # Тесты
├── alembic.ini         # Конфигурация миграций
├── docker-compose.yml  # Docker Compose конфигурация
├── Dockerfile          # Docker образ
├── main.py             # Точка входа
└── requirements.txt    # Зависимости
```

## 🧪 Тестирование

Проект включает unit, integration и functional тесты:

```bash
# Все тесты
pytest

# Конкретный тип тестов
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# С подробным выводом
pytest -v
```

## 🔌 API Endpoints

### Аутентификация
- `POST /auth/register` - Регистрация
- `POST /auth/login` - Вход
- `POST /auth/logout` - Выход
- `GET /auth/verify-email` - Подтверждение email
- `POST /auth/refresh` - Обновление токена
- `POST /auth/change-password` - Смена пароля

### Товары
- `GET /products/` - Список товаров (с фильтрацией)
- `GET /products/{slug}` - Детали товара
- `GET /products/category/{slug}` - Товары по категории
- `POST /products/` - Создание товара (только админ)

### Корзина
- `GET /cart/` - Получить корзину
- `POST /cart/add` - Добавить в корзину
- `PUT /cart/update/{item_id}` - Обновить количество
- `DELETE /cart/remove/{item_id}` - Удалить из корзины

### Заказы
- `POST /orders/` - Создать заказ
- `GET /orders/` - Список заказов пользователя
- `GET /orders/{order_id}` - Детали заказа
- `PUT /orders/{order_id}/cancel` - Отменить заказ

### Отзывы
- `POST /reviews/` - Создать отзыв
- `GET /reviews/product/{product_id}` - Отзывы товара
- `GET /reviews/search` - Поиск отзывов (админ)

### Админ-панель
- `GET /admin/` - Дашборд
- `GET /admin/products` - Управление товарами
- `GET /admin/orders` - Управление заказами
- `GET /admin/users` - Управление пользователями
- `GET /admin/reviews` - Управление отзывами

## 🛠️ Технологии

- **Backend**: FastAPI, Python 3.11+
- **База данных**: PostgreSQL 15, SQLAlchemy 2.0
- **Кэширование**: Redis
- **Очереди задач**: Celery
- **Аутентификация**: JWT (python-jose), Argon2
- **Миграции**: Alembic
- **Тестирование**: pytest, pytest-asyncio
- **Защита**: slowapi (rate limiting)
- **WebSocket**: FastAPI WebSocket
- **Шаблоны**: Jinja2
- **Обработка изображений**: Pillow

## 📝 Основные фичи

### Производительность
- ✅ Асинхронная обработка запросов
- ✅ Redis кэширование для часто запрашиваемых данных
- ✅ Фоновая обработка изображений через Celery
- ✅ Оптимизированные SQL запросы

### Безопасность
- ✅ Rate limiting на критичных endpoints
- ✅ Хеширование паролей (Argon2)
- ✅ JWT токены с версионированием
- ✅ Email верификация
- ✅ Защита от CSRF

### Функциональность
- ✅ Полноценная корзина и система заказов
- ✅ Система отзывов и рейтингов
- ✅ WebSocket чат в реальном времени
- ✅ Админ-панель с полным управлением
- ✅ Фильтрация и поиск товаров
- ✅ Управление пользователями

## 🔧 Разработка

### Создание миграций
```bash
alembic revision --autogenerate -m "описание изменений"
alembic upgrade head
```

### Запуск в режиме разработки
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Просмотр API документации
После запуска приложения:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📄 Лицензия

Этот проект создан в образовательных целях.

## 👤 Автор

Проект разработан для курсовой работы.

---

**Примечание**: Не забудьте изменить `SECRET_KEY` и другие секретные данные перед развертыванием в production!

