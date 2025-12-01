from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.dao.base import BaseDAO
from app.review.models import Review
from app.products.models import Product


class ReviewsDAO(BaseDAO):
    model = Review
    
    @classmethod
    async def find_by_product_name(cls, session: AsyncSession, product_name: str):
        """Ищет отзывы по названию товара (частичное совпадение, ILIKE)."""
        query = (
            select(Review)
            .join(Product, Review.product_id == Product.id)
            .where(Product.name.ilike(f"%{product_name}%"))
            .order_by(Review.created_at.desc())
        )
        result = await session.execute(query)
        return result.scalars().all()