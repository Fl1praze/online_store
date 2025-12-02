"""
Функциональные тесты для API продуктов.
Тестирование полного цикла работы API endpoints для продуктов.
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
@patch('app.products.routers.redis_client.get')
@patch('app.products.routers.redis_client.setex')
async def test_get_products_list(mock_redis_setex, mock_redis_get, async_client: AsyncClient, db_session, test_product):
    """
    Функциональный тест: получение списка продуктов через API
    """
    # Мокаем Redis - возвращаем None (кэш пуст)
    mock_redis_get.return_value = None
    
    # Получаем список продуктов
    response = await async_client.get("/products/", params={})
    
    # Проверяем успешный ответ
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем структуру ответа (должна быть структура с items, total, page, page_size)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    
    # Проверяем, что список не пустой (должен содержать наш тестовый продукт)
    assert len(data["items"]) > 0
    
    # Проверяем, что наш тестовый продукт есть в списке
    product_found = False
    for product in data["items"]:
        if product.get("id") == test_product.id or product.get("name") == test_product.name:
            product_found = True
            # Проверяем основные поля
            assert "name" in product
            assert "id" in product
            assert "price" in product
            break
    
    assert product_found, "Тестовый продукт должен быть в списке"

