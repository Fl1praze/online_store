import json

from fastapi import APIRouter, HTTPException, status, Depends
from app.review.schemas import ReviewCreate, ReviewResponse
from app.review.dao import ReviewsDAO
from app.products.dao import ProductsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.redis_client import redis_client
from datetime import datetime

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/")
async def add_review(
    review_data: ReviewCreate,
    current_user = Depends(get_current_user)
):
    product = await ProductsDAO.find_by_id(review_data.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing_review = await ReviewsDAO.find_one_or_none(
        user_id=current_user.id,
        product_id=review_data.product_id
    )
    if existing_review:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reviewed this product")


    new_review = await ReviewsDAO.add(
        user_id=current_user.id,
        product_id=review_data.product_id,
        rating=review_data.rating,
        comment=review_data.comment
    )

    return {"message": "review created successfully"}

@router.get("/product/{product_id}", response_model=list[ReviewResponse])
async def get_reviews_for_product(product_id: int):
    cache_key = f'reviews:{product_id}'
    cache_values = redis_client.get(cache_key)
    if cache_values:
        return json.loads(cache_values)
    product = await ProductsDAO.find_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Получаем отзывы
    reviews = await ReviewsDAO.find_all(product_id=product_id)

    list_reviews = [
        {
            'id':review.id,
            'user_id':review.user_id,
            'product_id':review.product_id,
            'rating':review.rating,
            'comment':review.comment,
            'created_at':review.created_at.isoformat() if isinstance(review.created_at, datetime) else review.created_at
        }
        for review in reviews
    ]
    redis_client.setex(cache_key,600,json.dumps(list_reviews))
    return reviews

@router.delete('/{review_id}')
async def delete_reviews_for_product(
        review_id:int,
        current_user = Depends(get_current_user)
):
    review = await ReviewsDAO.find_by_id(review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    user = current_user.id
    admin = current_user.is_admin
    if review.id != user and not admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    await ReviewsDAO.delete(review_id)
    redis_client.delete(f'reviews:{review.product_id}')
    return {"message": "review delete successfully"}
