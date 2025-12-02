"""
Модуль безопасности приложения
"""
from app.security.rate_limiter import limiter, get_client_ip

__all__ = ["limiter", "get_client_ip"]

