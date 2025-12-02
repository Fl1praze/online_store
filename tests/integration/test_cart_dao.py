"""
Интеграционные тесты для работы с корзиной (app/cart/dao.py)
Тестирование взаимодействия CartDAO, CartItemDAO и ProductsDAO.
"""
import pytest
from app.cart.dao import CartDAO, CartItemDAO
from app.products.dao import ProductsDAO


@pytest.mark.asyncio
async def test_cart_creation_and_item_addition(db_session, test_user, test_product):
    """
    Интеграционный тест: создание корзины и добавление товара
    """
    # Создаём корзину для пользователя
    cart_id = await CartDAO.add(
        db_session,
        user_id=test_user.id
    )
    await db_session.commit()
    
    # Проверяем, что корзина создана
    cart = await CartDAO.find_by_id(db_session, cart_id)
    assert cart is not None
    assert cart.user_id == test_user.id
    
    # Добавляем товар в корзину (нужно указать price)
    item_id = await CartItemDAO.add(
        db_session,
        cart_id=cart.id,
        product_id=test_product.id,
        quantity=2,
        price=test_product.price
    )
    await db_session.commit()
    
    # Проверяем, что товар добавлен
    item = await CartItemDAO.find_by_id(db_session, item_id)
    assert item is not None
    assert item.cart_id == cart.id
    assert item.product_id == test_product.id
    assert item.quantity == 2
    
    # Проверяем, что можем найти все товары корзины
    items = await CartItemDAO.find_all(db_session, cart_id=cart.id)
    assert len(items) == 1
    assert items[0].id == item_id

