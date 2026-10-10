import json
from app.redis_client import redis_client
from fastapi import APIRouter,HTTPException,status,Depends
from app.category.dao import CategoriesDAO
from app.category.schemas import CreateCategory
from slugify import slugify
from app.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.dependencies import get_current_user
router = APIRouter(prefix='/categories', tags=['category'])


@router.get('/')
async def get_all_categories(
        session: AsyncSession = Depends(get_async_session)
):
    cache_key = f'all_categories'
    cache_values = redis_client.get(cache_key)
    if cache_values:
        return json.loads(cache_values)
    result = await CategoriesDAO.find_all(session)

    data_list = [
        {
            'id': cate.id,
            'parent_id': cate.parent_id,
            'name': cate.name,
            'slug': cate.slug,
            'is_active': cate.is_active
        }
        for cate in result
    ]
    redis_client.setex(cache_key, 600, json.dumps(data_list))
    return result


@router.post('/', status_code=201, description='Для создания главной категории не отправлять parent_id')
async def create_category(
        data: CreateCategory,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)

):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        query = await CategoriesDAO.find_one_or_none(session, name=data.name)
        if not query:
            await CategoriesDAO.add(
                session,
                name=data.name,
                parent_id=data.parent_id,
                slug=slugify(data.name)
            )
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category already created')

    # очищаем кэш всех категорий и возможного кэша по слагу
    redis_client.delete('all_categories')
    redis_client.delete('categories:all')  # Кэш для shop страниц
    if data.parent_id is None:
        # на всякий случай чистим кэш корневых категорий по слагу
        redis_client.delete(f"category:{slugify(data.name)}")

    return {"message": "Category created successfully"}


@router.put('/{category_slug}')
async def update_category(
        category_slug: str,
        data: CreateCategory,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        existing_category = await CategoriesDAO.find_one_or_none(session, slug=category_slug)
        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no category found')
        await CategoriesDAO.update_by_slug(
            session,
            category_slug,
            **data.model_dump(),
            slug=slugify(data.name)
        )

    redis_client.delete(f'all_categories')
    redis_client.delete('categories:all')  # Кэш для shop страниц
    redis_client.delete(f'category:{category_slug}')
    return {'message': 'Category update is successful'}


@router.delete('/{category_slug}')
async def delete_category(
        category_slug: str,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        existing_category = await CategoriesDAO.find_one_or_none(session, slug=category_slug)
        if not existing_category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no category found')

        await CategoriesDAO.update_by_slug(session, category_slug, is_active=False)

    redis_client.delete(f'all_categories')
    redis_client.delete('categories:all')  # Кэш для shop страниц
    redis_client.delete(f'category:{category_slug}')
    return {"message": "Category deleted successfully (marked as inactive)"}
