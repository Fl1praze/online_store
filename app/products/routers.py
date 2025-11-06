import json
from http.client import HTTPException

from fastapi import APIRouter,HTTPException,status,File,UploadFile,Depends
from app.products.dao import ProductsDAO
from app.category.dao import CategoriesDAO
from app.products.schemas import CreateProduct,ResponseProduct
from slugify import slugify
from app.tasks import process_product_images_task
from app.redis_client import redis_client
from app.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.dependencies import get_current_user
router = APIRouter(prefix='/products', tags=['products'])


# with salary+redis
@router.post('/')
async def create_product(
        name: str,
        description: str,
        price: int,
        stock: int,
        category_id: int,
        small_image: UploadFile = File(...),
        large_image: UploadFile = File(...),
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        execute_category_id = await CategoriesDAO.find_one_or_none(session, id=category_id)
        if not execute_category_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='This category does not exist')

        query = await ProductsDAO.find_one_or_none(session, slug=slugify(name))
        if query:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Product already added')

        new_product_id = await ProductsDAO.add(
            session,
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


    small_content = await small_image.read()
    large_content = await large_image.read()
    task = process_product_images_task.delay(
        small_content,
        large_content,
        name)

    return {
        'message': 'Product created, images processing in background',
        'task_id': task.id,
        'product_id': new_product_id
    }


# with redis cache(memory)
@router.get('/')
async def all_products(
        session: AsyncSession = Depends(get_async_session)
):
    cache_key = 'products'
    cached_value = redis_client.get(cache_key)
    if cached_value:
        return json.loads(cached_value)

    products = await ProductsDAO.get_active_stock_products(session)
    if not products:
        raise HTTPException(status_code=404, detail="There are no products")

    products_list = [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "price": p.price,
            "stock": p.stock,
            "rating": p.rating,
            "is_active": p.is_active,
            'category_id': p.category_id,
            "small_image": p.small_image,
            "large_image": p.large_image,
        }
        for p in products
    ]
    redis_client.setex(cache_key, 600, json.dumps(products_list))
    return products


# with redis(memory)
@router.get('/{product_slug}')
async def get_product_quantity_by_slug(
        product_slug: str,
        session: AsyncSession = Depends(get_async_session)
):
    cache_key = f'product:{product_slug}'
    cached_value = redis_client.get(cache_key)
    if cached_value:
        return json.loads(cached_value)

    products = await ProductsDAO.find_one_or_none(session, slug=product_slug)
    if not products:
        raise HTTPException(status_code=404, detail='Products not found')

    products_is_active = products.is_active
    if not products_is_active:
        return {'message': 'Товар не активен'}

    products_quantity = products.stock
    if products_quantity <= 0:
        return {'message': 'Товара нет на складе'}

    product_dict = {
        "id": products.id,
        "name": products.name,
        "slug": products.slug,
        "description": products.description,
        "price": float(products.price),
        'small_image': products.small_image,
        'large_image': products.large_image,
        "stock": products.stock,
        'category_id': products.category_id,
        'rating': products.rating,
        "is_active": products.is_active,
    }
    redis_client.setex(cache_key, 600, json.dumps(product_dict))
    return products


# with redis cache
@router.get("/category/{category_slug}")
async def all_product_by_category_slug(
        category_slug: str,
        session: AsyncSession = Depends(get_async_session)
):
    cache_key = f'category:{category_slug}'
    cached_value = redis_client.get(cache_key)
    if cached_value:
        return json.loads(cached_value)

    category = await CategoriesDAO.find_one_or_none(session, slug=category_slug)
    if not category:
        raise HTTPException(404, "Category not found")

    category_ids = [category.id] + await CategoriesDAO.get_subcategories(session, category.id)
    result = await ProductsDAO.find_by_category_ids(session, category_ids)

    products_list = [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "price": p.price,
            "stock": p.stock,
            "rating": p.rating,
            "is_active": p.is_active,
            'category_id': p.category_id,
            "small_image": p.small_image,
            "large_image": p.large_image,
        }
        for p in result
    ]
    redis_client.setex(cache_key, 600, json.dumps(products_list))
    return result


@router.put('/{product_slug}')
async def update_product(
        product_slug: str,
        name: str,
        description: str,
        price: int,
        stock: int,
        category_id: int,
        small_image: UploadFile = File(...),
        large_image: UploadFile = File(...),
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        execute_old_name = await ProductsDAO.find_one_or_none(session, name=name)
        if execute_old_name and execute_old_name.slug != product_slug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар с таким названием уже существуеет")

        execute_slug = await ProductsDAO.find_one_or_none(session, slug=product_slug)
        if not execute_slug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no product found")

        execute_category = await CategoriesDAO.find_by_id(session, category_id)
        if not execute_category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no category found")

        await ProductsDAO.update_by_slug(
            session,
            product_slug,
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


    redis_client.delete(f'product:{product_slug}')
    redis_client.delete(f'product:{slugify(name)}')
    redis_client.delete(f'category: {product_slug}')
    redis_client.delete('products')

    return {"message": 'Product update is successful'}


@router.delete('/{product_slug}')
async def delete_product(
        product_slug: str,
        current_user = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    async with session.begin():
        if current_user.is_admin is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Доступ запрещён')
        execute_slug = await ProductsDAO.find_one_or_none(session, slug=product_slug)
        if not execute_slug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no product found")
        await ProductsDAO.update_by_slug(session, product_slug, is_active=False)

    redis_client.delete(f'product:{product_slug}')
    redis_client.delete(f'category: {product_slug}')  # ???
    redis_client.delete('products')

    return {'message': 'Product delete is successful'}
