from http.client import HTTPException

from fastapi import APIRouter,HTTPException,status
from app.products.dao import ProductsDAO
from app.category.dao import CategoriesDAO
from app.products.schemas import CreateProduct
from slugify import slugify

router = APIRouter(prefix='/products', tags=['products'])


@router.post('/')
async def create_product(data: CreateProduct):
    execute_category_id = await CategoriesDAO.find_one_or_none(id=data.category_id)
    if not execute_category_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='This category does not exist')

    query = await ProductsDAO.find_one_or_none(slug=slugify(data.name))
    if not query:
        await ProductsDAO.add(**data.model_dump(),slug=slugify(data.name),rating=0.0)
        return {'message':'Product add successful'}
    raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail='Product already added')


@router.get('/')
async def all_products():
    products = await ProductsDAO.get_active_stock_products()
    if not products:
        raise HTTPException(status_code=404, detail="There are no products")
    return products


@router.get('/{product_slug}')
async def get_product_quantity_by_slug(product_slug: str):
    products = await ProductsDAO.find_one_or_none(slug=product_slug)
    if not products:
        raise HTTPException(status_code=404,detail='Products not found')
    products_is_active = products.is_active
    if not products_is_active:
        return {'message':'Товар не активен'}
    products_quantity = products.stock
    if products_quantity <= 0:
        return {'message': 'Товара нет на складе'}
    return products



@router.get("/category/{category_slug}")
async def all_product_by_category_slug(category_slug: str):
    category = await CategoriesDAO.find_one_or_none(slug=category_slug)
    if not category:
        raise HTTPException(404, "Category not found")
    category_ids = [category.id] + await CategoriesDAO.get_subcategories(category.id)
    return await ProductsDAO.find_by_category_ids(category_ids)


@router.get('/detail/{product_slug}')
async def product_detail(product_slug: str):
    execute_slug = await ProductsDAO.find_one_or_none(slug=product_slug)
    if not execute_slug:
        raise  HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='There is no product found')
    return execute_slug


@router.put('/{product_slug}')
async def update_product(product_slug: str,data:CreateProduct):
    execute_slug = await ProductsDAO.find_one_or_none(slug=product_slug)
    if not execute_slug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="There is no product found")
    execute_category = await CategoriesDAO.find_by_id(data.category_id)
    if not execute_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="There is no category found")
    query = await ProductsDAO.update_by_slug(product_slug,**data.model_dump(),slug=slugify(data.name))
    return {"message":'Product update is successful'}


@router.delete('/{product_slug}')
async def delete_product(product_slug: str):
    execute_slug = await ProductsDAO.find_one_or_none(slug=product_slug)
    if not execute_slug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="There is no product found")
    query = await ProductsDAO.update_by_slug(product_slug,is_active=False)
    return {'message':'Product delete is successful'}
