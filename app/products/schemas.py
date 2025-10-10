from pydantic import BaseModel


class CreateProduct(BaseModel):
    name: str
    description: str
    price: int
    stock: int
    category_id: int


