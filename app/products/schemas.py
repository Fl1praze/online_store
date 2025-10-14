from pydantic import BaseModel


class CreateProduct(BaseModel):
    name: str
    description: str
    price: int
    stock: int
    category_id: int

    class Config:
        from_attributes = True

class ResponseProduct(BaseModel):
    name:str
    slug: str
    price:int
    category_id: int
    is_active: bool
    description: str
    small_image:str = None
    large_image:str = None
    stock: int
    rating : bool

    class Config:
        from_attributes = True


