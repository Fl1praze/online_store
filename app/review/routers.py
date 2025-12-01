import json

from fastapi import APIRouter, HTTPException, status, Depends
from app.review.schemas import ReviewCreate, ReviewResponse
from app.review.dao import ReviewsDAO
from app.products.dao import ProductsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.redis_client import redis_client
from app.orders.dao import OrderDAO, OrderItemDAO
from sqlalchemy import select, and_
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/")
async def add_review(
        review_data: ReviewCreate,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        product = await ProductsDAO.find_by_id(session, review_data.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        # Проверяем, заказывал ли пользователь этот товар
        user_orders = await OrderDAO.find_all(session, user_id=current_user.id)
        has_ordered = False
        for order in user_orders:
            order_items = await OrderItemDAO.find_all(session, order_id=order.id)
            for item in order_items:
                if item.product_id == review_data.product_id:
                    has_ordered = True
                    break
            if has_ordered:
                break
        
        if not has_ordered:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете оставить отзыв только на товар, который вы заказали"
            )

        existing_review = await ReviewsDAO.find_one_or_none(
            session,
            user_id=current_user.id,
            product_id=review_data.product_id
        )
        if existing_review:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You have already reviewed this product")

        await ReviewsDAO.add(
            session,
            user_id=current_user.id,
            product_id=review_data.product_id,
            rating=review_data.rating,
            comment=review_data.comment
        )

        old_rating = product.rating
        old_count_review = product.review_count or 0
        review_rating = review_data.rating
        if old_rating == 0.0:
            new_rating = review_data.rating
        else:
            new_rating = round((old_rating * old_count_review + review_rating) / (old_count_review + 1), 1)

        await ProductsDAO.update(session, product.id, rating=new_rating, review_count=old_count_review + 1)

    return {"message": "review created successfully"}


@router.get("/product/{product_id}", response_model=list[ReviewResponse])
async def get_reviews_for_product(
        product_id: int,
        session: AsyncSession = Depends(get_async_session)
):
    cache_key = f'reviews:{product_id}'
    cache_values = redis_client.get(cache_key)
    if cache_values:
        return json.loads(cache_values)

    product = await ProductsDAO.find_by_id(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    reviews = await ReviewsDAO.find_all(session, product_id=product_id)

    list_reviews = [
        {
            'id': review.id,
            'user_id': review.user_id,
            'product_id': review.product_id,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat() if isinstance(review.created_at,
                                                                      datetime) else review.created_at
        }
        for review in reviews
    ]
    redis_client.setex(cache_key, 600, json.dumps(list_reviews))
    return reviews


@router.get("/search")
async def search_reviews_by_product_name(
        product_name: str,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    """Поиск отзывов по названию товара (только для админов)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Только для администраторов."
        )
    
    reviews = await ReviewsDAO.find_by_product_name(session, product_name)
    
    # Получаем информацию о товарах для каждого отзыва
    from app.products.dao import ProductsDAO
    list_reviews = []
    for review in reviews:
        product = await ProductsDAO.find_by_id(session, review.product_id)
        list_reviews.append({
            'id': review.id,
            'user_id': review.user_id,
            'product_id': review.product_id,
            'product_name': product.name if product else f"Товар #{review.product_id}",
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat() if isinstance(review.created_at,
                                                                      datetime) else review.created_at
        })
    return list_reviews


@router.delete('/{review_id}')
async def delete_reviews_for_product(
        review_id: int,
        current_user: Users = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):

    async with session.begin():
        review = await ReviewsDAO.find_by_id(session, review_id)
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

        user = current_user.id
        admin = current_user.is_admin
        if review.user_id != user and not admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        product_id = review.product_id
        await ReviewsDAO.delete(session, review_id)

    redis_client.delete(f'reviews:{product_id}')
    return {"message": "review delete successfully"}