from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

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

# Подключаем rate limiter к приложению
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Публичный фронт магазина
app.include_router(shop_router)

# API
app.include_router(users_routers)
app.include_router(category_routers)
app.include_router(products_routers)
app.include_router(review_router)
app.include_router(cart_routers)
app.include_router(order_router)
app.include_router(chat_router)

# Админка
app.include_router(admin_router)

