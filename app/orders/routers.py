from fastapi import APIRouter, HTTPException, status, Depends
from app.orders.models import Order, OrderItem
from app.cart.models import Cart, CartItem
from app.products.models import Product
from app.orders.schemas import OrderCreate, OrderResponse
from app.cart.dao import CartDAO, CartItemDAO
from app.products.dao import ProductsDAO
from app.orders.dao import OrderDAO, OrderItemDAO
from app.users.dependencies import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_user)
):

    cart = await CartDAO.find_one_or_none(user_id=current_user.id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    cart_items = await CartItemDAO.find_all(cart_id=cart.id)

    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    total_amount = sum(item.quantity * item.price for item in cart_items)

    order_id = await OrderDAO.add_order(
        user_id=current_user.id,
        total_amount=total_amount,
        shipping_address=order_data.shipping_address,
        payment_method=order_data.payment_method,
        status="pending"
    )

    for item in cart_items:
        await OrderItemDAO.add(
            order_id=order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )


        product = await ProductsDAO.find_by_id(item.product_id)
        if product.stock < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock")
        await ProductsDAO.update(product.id, stock=product.stock - item.quantity)

    for item in cart_items:
        await CartItemDAO.delete(item.id)

    # Загружаем созданный заказ
    new_order = await OrderDAO.find_by_id(order_id)
    order_items = await OrderItemDAO.find_all(order_id=order_id)
    new_order.items = order_items

    return new_order

@router.get("/", response_model=list[OrderResponse])
async def get_user_orders(
    current_user = Depends(get_current_user)
):

    orders = await OrderDAO.find_all(user_id=current_user.id)

    for order in orders:
        order_items = await OrderItemDAO.find_all(order_id=order.id)
        order.items = order_items

    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user = Depends(get_current_user)
):

    order = await OrderDAO.find_one_or_none(id=order_id, user_id=current_user.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


    order_items = await OrderItemDAO.find_all(order_id=order.id)
    order.items = order_items

    return order

@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user = Depends(get_current_user)
):

    order = await OrderDAO.find_one_or_none(id=order_id, user_id=current_user.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


    if order.status not in ["pending", "processing"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this order")


    await OrderDAO.update(order.id, status="cancelled")

    order = await OrderDAO.find_by_id(order.id)
    order_items = await OrderItemDAO.find_all(order_id=order.id)
    order.items = order_items

    return order