from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.orders.models import  OrderStatus
from app.orders.schemas import OrderCreate, OrderResponse
from app.cart.dao import CartDAO, CartItemDAO
from app.products.dao import ProductsDAO
from app.orders.dao import OrderDAO, OrderItemDAO
from app.users.dependencies import get_current_user
from app.users.models import Users

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse)
async def create_order(
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
    updated_order = None

    async with session.begin():
        order = await OrderDAO.find_one_or_none(session, id=order_id, user_id=current_user.id)

        if not order:
            if current_user.is_admin:
                order = await OrderDAO.find_by_id(session, order_id)

            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


        if order.status not in [OrderStatus.pending, OrderStatus.processing]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this order")

        await OrderDAO.update(session, order.id, status=OrderStatus.cancelled)


    updated_order = await OrderDAO.find_by_id(session, order_id)
    order_items = await OrderItemDAO.find_all(session, order_id=order_id)
    updated_order.items = order_items

    return updated_order

