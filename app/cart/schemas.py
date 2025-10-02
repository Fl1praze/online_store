from pydantic import BaseModel


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]

    class Config:
        from_attributes = True