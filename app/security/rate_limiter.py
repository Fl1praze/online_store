from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


# Функция для получения IP адреса клиента
def get_client_ip(request: Request) -> str:
    """
    Получает IP адрес клиента из запроса.
    """
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Берем первый IP из списка (оригинальный клиент)
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Если нет заголовков, используем стандартный метод
    return get_remote_address(request)


# Создаём лимитер
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200/hour"]  # Общий лимит по умолчанию
)


# Защита от брутфорса - логин
LOGIN_LIMIT = "5/minute"  # 5 попыток в минуту

# Защита от спама - регистрация
REGISTER_LIMIT = "3/hour"  # 3 регистрации в час

# Защита от массового создания заказов (защита от спама кнопки)
ORDER_LIMIT = "10/minute"  # 10 заказов в минуту (защита от случайных/намеренных массовых заказов)

# Защита от спама добавления в корзину
CART_ADD_LIMIT = "30/minute"  # 30 добавлений в минуту

# Поиск и фильтрация (защита от DDoS на поиск)
SEARCH_LIMIT = "60/minute"  # 60 запросов в минуту

