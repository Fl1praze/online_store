
from fastapi import APIRouter,HTTPException,status
from app.category.dao import CategoriesDAO
from app.category.schemas import CreateCategory
from slugify import slugify

router = APIRouter(prefix='/categories', tags=['category'])

@router.get('/')
async def get_all_categories():
    result = CategoriesDAO.find_all()
    return await result


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
    return {'message':'Category update is successful'}


@router.delete('/{category_slug}')
async def delete_category(category_slug: str):
    existing_category = await CategoriesDAO.find_one_or_none(slug=category_slug)
    if existing_category:
        await CategoriesDAO.update_by_slug(category_slug, is_active=False)
        return {"message": "Category deleted successfully (marked as inactive)"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='There is no category found')