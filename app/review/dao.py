from app.dao.base import BaseDAO
from app.review.models import Review


class ReviewsDAO(BaseDAO):
    model = Review