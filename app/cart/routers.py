from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import async_session_maker
from app.cart.models import Cart, CartItem
from app.products.models import Product
from app.cart.schemas import CartItemCreate, CartResponse
from app.users.dependencies import get_current_user
from app.cart.dao import CartDAO,CartItemDAO
from app.products.dao import ProductsDAO

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='нужно авторизоваться')
    cart = await CartDAO.find_one_or_none(user_id=current_user.id)
    if not cart:
        # Создаём корзину, если её нет
        await CartDAO.add(user_id=current_user.id)
        cart = await CartDAO.find_one_or_none(user_id=current_user.id)

    # Загружаем товары в корзине
    items = await CartItemDAO.find_all(cart_id=cart.id)
    cart.items = items
    return cart


@router.post("/add")
async def add_to_cart(
    item_data: CartItemCreate,
    current_user = Depends(get_current_user)
):
    # Получаем корзину пользователя
    cart = await CartDAO.find_one_or_none(user_id=current_user.id)
    if not cart:
        # Создаём корзину, если её нет
        await CartDAO.add(user_id=current_user.id)
        cart = await CartDAO.find_one_or_none(user_id=current_user.id)

    # Получаем товар
    product = await ProductsDAO.find_by_id(item_data.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Проверяем, достаточно ли товара на складе
    if product.stock < item_data.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock")

    # Проверяем, есть ли уже такой товар в корзине
    existing_item = await CartItemDAO.find_one_or_none(
        cart_id=cart.id,
        product_id=item_data.product_id
    )

    if existing_item:
        # Обновляем количество
        await CartItemDAO.update(
            existing_item.id,
            quantity=existing_item.quantity + item_data.quantity
        )
    else:
        # Создаём новый элемент корзины
        await CartItemDAO.add(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            price=product.price
        )

    return {"message": "Item added to cart"}


@router.delete("/remove/{product_id}")
async def remove_from_cart(
    product_id: int,
    current_user = Depends(get_current_user)
):
    # Получаем корзину пользователя
    cart = await CartDAO.find_one_or_none(user_id=current_user.id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    # Находим товар в корзине
    item = await CartItemDAO.find_one_or_none(
        cart_id=cart.id,
        product_id=product_id
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

    # Удаляем товар из корзины
    await CartItemDAO.delete(item.id)
    return {"message": "Item removed from cart"}


@router.delete("/clear")
async def clear_cart(
    current_user = Depends(get_current_user)
):

    cart = await CartDAO.find_one_or_none(user_id=current_user.id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    # Удаляем все товары из корзины
    items = await CartItemDAO.find_all(cart_id=cart.id)
    for item in items:
        await CartItemDAO.delete(item.id)

    return {"message": "Cart cleared"}