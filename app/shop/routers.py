from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.products.dao import ProductsDAO
from app.products.schemas import ProductFilter
from app.category.dao import CategoriesDAO
from app.review.dao import ReviewsDAO
from app.users.dependencies import get_current_user, get_token
from app.users.models import Users
from app.cart.dao import CartDAO, CartItemDAO
from app.orders.schemas import OrderCreate
from app.orders.dao import OrderDAO, OrderItemDAO
from sqlalchemy import select, and_


router = APIRouter(tags=["Shop"])
templates = Jinja2Templates(directory="templates")


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Users | None:
    """
    Возвращает текущего пользователя, если есть токен, иначе None.
    Нужен для публичных страниц, чтобы не кидать 401.
    """
    try:
        token = get_token(request)
    except HTTPException:
        return None
    return await get_current_user(token=token, session=session)


@router.get("/", response_class=HTMLResponse)
async def shop_index(
    request: Request,
    filters: ProductFilter = Depends(),
    session: AsyncSession = Depends(get_async_session),
    current_user: Users | None = Depends(get_current_user_optional),
):
    products_page = await ProductsDAO.find_all_with_filters(session, filters)
    categories = await CategoriesDAO.find_all(session)
    return templates.TemplateResponse(
        "shop/index.html",
        {
            "request": request,
            "products_page": products_page,
            "categories": categories,
            "filters": filters,
            "current_category": None,  # На главной странице нет выбранной категории
            "user": current_user,
        },
    )


@router.get("/product/{slug}", response_class=HTMLResponse)
async def product_detail(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: Users | None = Depends(get_current_user_optional),
):
    product = await ProductsDAO.find_one_or_none(session, slug=slug)
    if not product or not product.is_active:
        return templates.TemplateResponse(
            "shop/not_found.html",
            {"request": request, "message": "Товар не найден или не активен"},
            status_code=404,
        )

    reviews = await ReviewsDAO.find_all(session, product_id=product.id)

    # Проверяем, заказывал ли пользователь этот товар (для возможности оставить отзыв)
    can_review = False
    if current_user:
        user_orders = await OrderDAO.find_all(session, user_id=current_user.id)
        for order in user_orders:
            order_items = await OrderItemDAO.find_all(session, order_id=order.id)
            for item in order_items:
                if item.product_id == product.id:
                    can_review = True
                    break
            if can_review:
                break

    return templates.TemplateResponse(
        "shop/product_detail.html",
        {
            "request": request,
            "product": product,
            "reviews": reviews,
            "user": current_user,
            "can_review": can_review,
        },
    )


@router.get("/category/{slug}", response_class=HTMLResponse)
async def products_by_category(
    slug: str,
    request: Request,
    filters: ProductFilter = Depends(),
    session: AsyncSession = Depends(get_async_session),
    current_user: Users | None = Depends(get_current_user_optional),
):
    category = await CategoriesDAO.find_one_or_none(session, slug=slug)
    if not category:
        return templates.TemplateResponse(
            "shop/not_found.html",
            {"request": request, "message": "Категория не найдена"},
            status_code=404,
        )

    # Получаем все подкатегории (бренды) для этой категории
    subcategory_ids = await CategoriesDAO.get_subcategories(session, category.id)
    # Список ID: сама категория + все её подкатегории
    category_ids = [category.id] + subcategory_ids
    # Фиксируем фильтр по всем категориям (родительская + дочерние)
    filters.category_id = category_ids
    products_page = await ProductsDAO.find_all_with_filters(session, filters)
    categories = await CategoriesDAO.find_all(session)

    return templates.TemplateResponse(
        "shop/index.html",
        {
            "request": request,
            "products_page": products_page,
            "categories": categories,
            "filters": filters,
            "current_category": category,
            "user": current_user,
        },
    )


@router.get("/cart", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    current_user: Users | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_async_session),
):
    # Если пользователь не авторизован, редиректим на страницу логина
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    cart = await CartDAO.find_one_or_none(session, user_id=current_user.id)
    items = []
    total = 0
    if cart:
        items = await CartItemDAO.find_all(session, cart_id=cart.id)
        # Получаем информацию о товарах для каждого элемента корзины
        for item in items:
            product = await ProductsDAO.find_by_id(session, item.product_id)
            if product:
                item.product_name = product.name
                item.product_slug = product.slug
                item.product_image = product.small_image
            else:
                item.product_name = f"Товар #{item.product_id}"
                item.product_slug = None
                item.product_image = None
        total = sum(i.quantity * i.price for i in items)

    return templates.TemplateResponse(
        "shop/cart.html",
        {
            "request": request,
            "cart": cart,
            "items": items,
            "total": total,
            "user": current_user,
        },
    )


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: Users | None = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        "shop/auth_login.html",
        {"request": request, "user": current_user},
    )


@router.get("/auth/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: Users | None = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        "shop/auth_register.html",
        {"request": request, "user": current_user},
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    orders = await OrderDAO.find_all(session, user_id=current_user.id)
    for order in orders:
        order_items = await OrderItemDAO.find_all(session, order_id=order.id)
        # Получаем информацию о товарах для каждого элемента заказа
        for item in order_items:
            product = await ProductsDAO.find_by_id(session, item.product_id)
            if product:
                item.product_name = product.name
                item.product_slug = product.slug
            else:
                item.product_name = f"Товар #{item.product_id}"
                item.product_slug = None
        order.items = order_items

    return templates.TemplateResponse(
        "shop/profile.html",
        {"request": request, "user": current_user, "orders": orders},
    )


