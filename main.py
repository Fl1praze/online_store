from fastapi import FastAPI

#Improt routers
from app.category.routers import router as category_routers
from app.products.routers import router as products_routers
from app.users.routers import router as users_routers


app = FastAPI()

app.include_router(users_routers)
app.include_router(category_routers)
app.include_router(products_routers)



