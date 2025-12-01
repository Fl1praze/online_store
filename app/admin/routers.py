from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.users.dependencies import get_current_user
from app.users.models import Users


router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    if not current_user.is_admin:
        # Простая защита админки
        return templates.TemplateResponse(
            "admin/forbidden.html",
            {"request": request, "user": current_user},
            status_code=403,
        )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/products", response_class=HTMLResponse)
async def admin_products_page(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    if not current_user.is_admin:
        return templates.TemplateResponse(
            "admin/forbidden.html",
            {"request": request, "user": current_user},
            status_code=403,
        )

    return templates.TemplateResponse(
        "admin/products.html",
        {"request": request, "user": current_user},
    )


@router.get("/categories", response_class=HTMLResponse)
async def admin_categories_page(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    if not current_user.is_admin:
        return templates.TemplateResponse(
            "admin/forbidden.html",
            {"request": request, "user": current_user},
            status_code=403,
        )

    return templates.TemplateResponse(
        "admin/categories.html",
        {"request": request, "user": current_user},
    )


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_page(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    if not current_user.is_admin:
        return templates.TemplateResponse(
            "admin/forbidden.html",
            {"request": request, "user": current_user},
            status_code=403,
        )

    return templates.TemplateResponse(
        "admin/orders.html",
        {"request": request, "user": current_user},
    )


@router.get("/reviews", response_class=HTMLResponse)
async def admin_reviews_page(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    if not current_user.is_admin:
        return templates.TemplateResponse(
            "admin/forbidden.html",
            {"request": request, "user": current_user},
            status_code=403,
        )

    return templates.TemplateResponse(
        "admin/reviews.html",
        {"request": request, "user": current_user},
    )


