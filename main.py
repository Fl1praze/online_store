from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

#Improt routers
from app.category.routers import router as category_routers
from app.products.routers import router as products_routers
from app.users.routers import router as users_routers
from app.cart.routers import router as cart_routers
from app.orders.routers import router as order_router
from app.review.routers import router as review_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(users_routers)
app.include_router(category_routers)
app.include_router(products_routers)
app.include_router(review_router)
app.include_router(cart_routers)
app.include_router(order_router)




