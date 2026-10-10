from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

#Improt routers
from app.category.routers import router as category_routers
from app.products.routers import router as products_routers
from app.users.routers import router as users_routers
from app.cart.routers import router as cart_routers
from app.orders.routers import router as order_router
from app.review.routers import router as review_router
from app.chat.router import router as chat_router
from app.admin.routers import router as admin_router
from app.shop.routers import router as shop_router
from app.security.rate_limiter import limiter

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.include_router(shop_router)

# API
app.include_router(users_routers)
app.include_router(category_routers)
app.include_router(products_routers)
app.include_router(review_router)
app.include_router(cart_routers)
app.include_router(order_router)
app.include_router(chat_router)

# for admin
app.include_router(admin_router)

#for error
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        if err.get("type") == "value_error":
            messages.append(err["msg"].removeprefix("Value error, "))
    if not messages:
        messages.append("Проверьте правильность введённых данных")
    return JSONResponse(
        status_code=422,
        content={"detail": " ".join(dict.fromkeys(messages))},
    )

