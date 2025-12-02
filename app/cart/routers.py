from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.cart.schemas import CartItemCreate, CartResponse
from app.users.dependencies import get_current_user
from app.cart.dao import CartDAO,CartItemDAO
from app.products.dao import ProductsDAO
from app.security.rate_limiter import limiter, CART_ADD_LIMIT

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
    if not cart:
        async with session.begin():
            cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
            if not cart:
                new_cart_id = await CartDAO.add(session, user_id=current_user.id)
                cart = await CartDAO.find_by_id(session, new_cart_id)

    items = await CartItemDAO.find_all(session, cart_id=cart.id)
    cart.items = items
    return cart


@router.post("/add")
@limiter.limit(CART_ADD_LIMIT)
async def add_to_cart(
        request: Request,
        item_data: CartItemCreate,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
        if not cart:
            new_cart_id = await CartDAO.add(session, user_id=current_user.id)
            cart = await CartDAO.find_by_id(session, new_cart_id)

        product = await ProductsDAO.find_by_id(session, item_data.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        if product.stock < item_data.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock")

        existing_item = await CartItemDAO.find_one_or_none(
            session,
            cart_id=cart.id,
            product_id=item_data.product_id
        )

        if existing_item:
            await CartItemDAO.update(
                session,
                existing_item.id,
                quantity=existing_item.quantity + item_data.quantity
            )
        else:
            await CartItemDAO.add(
                session,
                cart_id=cart.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price=product.price
            )

    return {"message": "Item added to cart"}


@router.delete("/remove/{product_id}")
async def remove_from_cart(
        product_id: int,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        item = await CartItemDAO.find_one_or_none(
            session,
            cart_id=cart.id,
            product_id=product_id
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

        await CartItemDAO.delete(session, item.id)

    return {"message": "Item removed from cart"}


@router.delete("/clear")
async def clear_cart(
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        items = await CartItemDAO.find_all(session, cart_id=cart.id)
        for item in items:
            await CartItemDAO.delete(session, item.id)

    return {"message": "Cart cleared"}