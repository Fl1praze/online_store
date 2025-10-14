import json

from app.redis_client import redis_client
from fastapi import APIRouter,HTTPException,status
from app.category.dao import CategoriesDAO
from app.category.schemas import CreateCategory
from slugify import slugify

router = APIRouter(prefix='/categories', tags=['category'])

@router.get('/')
async def get_all_categories():
    cache_key = f'all_categories'
    cache_values = redis_client.get(cache_key)
    if cache_values:
        return json.loads(cache_values)
    result = await CategoriesDAO.find_all()

    data_list = [
        {
            'id':cate.id,
            'parent_id':cate.parent_id,
            'name':cate.name,
            'slug':cate.slug,
            'is_active':cate.is_active
        }
        for cate in result
    ]
    redis_client.setex(cache_key,600,json.dumps(data_list))
    return result


#Сделать ошибку если уже существует такая категория
@router.post('/',status_code=201,description='Для создания главной категории не отправлять parent_id')
async def create_category(data: CreateCategory):
    query =  await CategoriesDAO.find_one_or_none(name=data.name)
    if not query:
        await CategoriesDAO.add(name=data.name, parent_id=data.parent_id, slug=slugify(data.name))
        return {"message": "Category created successfully"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='Category already created')


@router.put('/{category_slug}')
async def update_category(category_slug: str,data: CreateCategory):
    existing_category = await CategoriesDAO.find_one_or_none(slug=category_slug)
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found')
    await CategoriesDAO.update_by_slug(
        category_slug,
        **data.model_dump(),
        slug=slugify(data.name)
    )
    redis_client.delete(f'all_categories')
    return {'message':'Category update is successful'}


@router.delete('/{category_slug}')
async def delete_category(category_slug: str):
    existing_category = await CategoriesDAO.find_one_or_none(slug=category_slug)
    if not existing_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no category found')

    await CategoriesDAO.update_by_slug(category_slug, is_active=False)
    redis_client.delete('all_categories')
    return {"message": "Category deleted successfully (marked as inactive)"}
