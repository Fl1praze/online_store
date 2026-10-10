from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.orders.models import  OrderStatus
from app.orders.schemas import OrderCreate, OrderResponse
from app.cart.dao import CartDAO, CartItemDAO
from app.products.dao import ProductsDAO
from app.orders.dao import OrderDAO, OrderItemDAO
from app.review.dao import ReviewsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.security.rate_limiter import limiter, ORDER_LIMIT
from app.redis_client import redis_client

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse)
@limiter.limit(ORDER_LIMIT)
async def create_order(
        request: Request,
        order_data: OrderCreate,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    order_id = None

    async with session.begin():
        cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        cart_items = await CartItemDAO.find_all(session, cart_id=cart.id)
        if not cart_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        total_amount = sum(item.quantity * item.price for item in cart_items)

        order_id = await OrderDAO.add_order(
            session,
            user_id=current_user.id,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            payment_method=order_data.payment_method,
            status=OrderStatus.pending
        )

        for item in cart_items:
            product = await ProductsDAO.find_by_id(session, item.product_id)

            if not product or product.stock < item.quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Not enough stock for product {product.name if product else 'N/A'}")

            await ProductsDAO.update(session, product.id, stock=product.stock - item.quantity)

            await OrderItemDAO.add(
                session,
                order_id=order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )


        for item in cart_items:
            await CartItemDAO.delete(session, item.id)



    new_order = await OrderDAO.find_by_id(session, order_id)
    order_items = await OrderItemDAO.find_all(session, order_id=order_id)


    new_order.items = order_items

    return new_order


@router.get("/", response_model=list[OrderResponse])
async def get_user_orders(
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):

    orders = await OrderDAO.find_all(session, user_id=current_user.id)

    for order in orders:
        order_items = await OrderItemDAO.find_all(session, order_id=order.id)
        order.items = order_items

    return orders


@router.get('/get_all_orders', response_model=list[OrderResponse])
async def get_all_orders(
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Доступ запрещён')

    orders = await OrderDAO.find_all(session)

    for order in orders:
        order_items = await OrderItemDAO.find_all(session, order_id=order.id)
        order.items = order_items
        # Получаем email пользователя
        if order.user_id:
            from app.users.dao import UsersDAO
            user = await UsersDAO.find_by_id(session, order.user_id)
            if user:
                order.user_email = user.email
                order.user_username = user.username
            else:
                order.user_email = None
                order.user_username = None
        else:
            order.user_email = None
            order.user_username = None
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
        order_id: int,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    order = await OrderDAO.find_one_or_none(session, id=order_id, user_id=current_user.id)

    if not order:
        if current_user.is_admin:
            order = await OrderDAO.find_by_id(session, order_id)

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order_items = await OrderItemDAO.find_all(session, order_id=order.id)
    order.items = order_items

    return order


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
        order_id: int,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        order = await OrderDAO.find_one_or_none(session, id=order_id, user_id=current_user.id)

        if not order:
            if current_user.is_admin:
                order = await OrderDAO.find_by_id(session, order_id)

            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if order.status not in [OrderStatus.pending, OrderStatus.processing]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Невозможно отменить заказ с текущим статусом")

        # Возвращаем товары на склад
        order_items = await OrderItemDAO.find_all(session, order_id=order_id)
        product_ids = set()  # Для отслеживания товаров, у которых нужно пересчитать рейтинг
        
        for item in order_items:
            product = await ProductsDAO.find_by_id(session, item.product_id)
            if product:
                await ProductsDAO.update(session, product.id, stock=product.stock + item.quantity)
                product_ids.add(item.product_id)
        
        # Удаляем отзывы пользователя по товарам из этого заказа
        for product_id in product_ids:
            review = await ReviewsDAO.find_one_or_none(
                session,
                user_id=current_user.id,
                product_id=product_id
            )
            
            if review:
                # Получаем товар для пересчета рейтинга
                product = await ProductsDAO.find_by_id(session, product_id)
                if product:
                    old_rating = product.rating or 0.0
                    old_count = product.review_count or 0
                    deleted_rating = review.rating
                    
                    # Удаляем отзыв
                    await ReviewsDAO.delete(session, review.id)
                    
                    # Пересчитываем рейтинг товара
                    if old_count <= 1:
                        # Если был только один отзыв, обнуляем рейтинг
                        new_rating = 0.0
                        new_count = 0.0
                    else:
                        # Формула обратная добавлению: (old_rating * old_count - deleted_rating) / (old_count - 1)
                        new_rating = round((old_rating * old_count - deleted_rating) / (old_count - 1), 1)
                        new_count = old_count - 1
                    
                    await ProductsDAO.update(session, product_id, rating=new_rating, review_count=new_count)
                    
                    # Очищаем кэш Redis для этого товара
                    redis_client.delete(f'reviews:{product_id}')
                    if product.slug:
                        redis_client.delete(f'product:{product.slug}')
                    # Очищаем все кэши товаров (на случай если товар в списке)
                    product_list_keys = redis_client.keys('products:*')
                    if product_list_keys:
                        redis_client.delete(*product_list_keys)

        # Отменяем заказ
        await OrderDAO.update(session, order.id, status=OrderStatus.cancelled)

    updated_order = await OrderDAO.find_by_id(session, order_id)
    order_items = await OrderItemDAO.find_all(session, order_id=order_id)
    
    # Получаем информацию о товарах для каждого элемента заказа
    for item in order_items:
        product = await ProductsDAO.find_by_id(session, item.product_id)
        if product:
            item.product_name = product.name
            item.product_slug = product.slug
            item.product_image = product.small_image
        else:
            item.product_name = f"Товар #{item.product_id}"
            item.product_slug = None
            item.product_image = None
    
    updated_order.items = order_items

    return updated_order

