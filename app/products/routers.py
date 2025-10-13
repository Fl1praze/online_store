import json
from http.client import HTTPException

from fastapi import APIRouter,HTTPException,status,File,UploadFile
from app.products.dao import ProductsDAO
from app.category.dao import CategoriesDAO
from app.products.schemas import CreateProduct,ResponseProduct
from slugify import slugify
from app.tasks import process_product_images_task
from app.redis_client import redis_client

router = APIRouter(prefix='/products', tags=['products'])


@router.post('/')
async def create_product(
        name:str,
        description:str,
        price:int,
        stock:int,
        category_id:int,
        small_image: UploadFile = File(...),
        large_image: UploadFile = File(...)
):
    execute_category_id = await CategoriesDAO.find_one_or_none(id=category_id)
    if not execute_category_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='This category does not exist')

    query = await ProductsDAO.find_one_or_none(slug=slugify(name))
    if  query:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Product already added')

    small_content = await small_image.read()
    large_content = await large_image.read()

    task = process_product_images_task.delay(
        small_content,
        large_content,
        name)

    new_product = await ProductsDAO.add(
        name=name,
        slug=slugify(name),
        description=description,
        price=price,
        stock=stock,
        category_id=category_id,
        small_image=f'{slugify(name)}_small.jpg',
        large_image=f"{slugify(name)}_large.jpg",
        rating=0.0
    )

    return {
        'message': 'Product created, images processing in background',
        'task_id': task.id
    }


@router.get('/')
async def all_products():
    products = await ProductsDAO.get_active_stock_products()
    if not products:
        raise HTTPException(status_code=404, detail="There are no products")
    return products


@router.get('/{product_slug}')
async def get_product_quantity_by_slug(product_slug: str):
    cache_key = f'product:{product_slug}'
    cached_value = redis_client.get(cache_key)
    if cached_value:
        return json.loads(cached_value)

    products = await ProductsDAO.find_one_or_none(slug=product_slug)
    if not products:
        raise HTTPException(status_code=404,detail='Products not found')

    products_is_active = products.is_active
    if not products_is_active:
        return {'message':'Товар не активен'}

    products_quantity = products.stock
    if products_quantity <= 0:
        return {'message': 'Товара нет на складе'}

    product_dict = {
        "id": products.id,
        "name": products.name,
        "slug": products.slug,
        "description": products.description,
        "price": float(products.price),
        'small_image':products.small_image,
        'large_image':products.large_image,
        "stock": products.stock,
        'category_id':products.category_id,
        'rating':products.rating,
        "is_active": products.is_active,
    }
    redis_client.setex(cache_key, 600, json.dumps(product_dict))
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
