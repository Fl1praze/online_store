from app.dao.base import BaseDAO
from app.products.models import Product
from sqlalchemy import select,and_,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.products.schemas import ProductFilter



class ProductsDAO(BaseDAO):
    model = Product

    @classmethod
    async def get_active_stock_products(cls, session: AsyncSession):
        query = select(cls.model).where(
            and_(cls.model.is_active == True, cls.model.stock > 0)
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def find_by_category_ids(cls, session: AsyncSession, category_ids: list[int]):
        query = select(cls.model).where(
            cls.model.category_id.in_(category_ids),
            cls.model.is_active == True,
            cls.model.stock > 0
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def find_all_with_filters(cls, session: AsyncSession, filter_params: ProductFilter):
        """
        Ищет товары по фильтрам с пагинацией.
        Возвращает словарь с товарами и общим количеством.
        """
        # 1. Собираем список условий для WHERE
        # Базовое условие: товар должен быть активен
        filters = [cls.model.is_active == True]

        if filter_params.category_id is not None:
            # Если category_id - это список, используем IN, иначе просто равенство
            if isinstance(filter_params.category_id, list):
                filters.append(cls.model.category_id.in_(filter_params.category_id))
            else:
                filters.append(cls.model.category_id == filter_params.category_id)
        
        if filter_params.min_price is not None:
            filters.append(cls.model.price >= filter_params.min_price)
            
        if filter_params.max_price is not None:
            filters.append(cls.model.price <= filter_params.max_price)
            
        if filter_params.in_stock is not None:
            if filter_params.in_stock:
                filters.append(cls.model.stock > 0)
            else:
                filters.append(cls.model.stock == 0)

        if filter_params.name is not None:
            # частичный поиск по названию, нечувствителен к регистру
            filters.append(cls.model.name.ilike(f"%{filter_params.name}%"))

        # 2. Считаем общее количество (TOTAL) для пагинации
        # Мы используем те же фильтры, что и для выборки
        count_query = select(func.count()).select_from(cls.model).where(*filters)
        total = await session.scalar(count_query) or 0

        # 3. Делаем выборку самих товаров (ITEMS)
        query = (
            select(cls.model)
            .where(*filters)
            .order_by(cls.model.id)
            .offset((filter_params.page - 1) * filter_params.page_size)
            .limit(filter_params.page_size)
        )
        result = await session.execute(query)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": filter_params.page,
            "page_size": filter_params.page_size
        }

