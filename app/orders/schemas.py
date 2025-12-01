from pydantic import BaseModel
from datetime import datetime

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    shipping_address: str
    payment_method: str

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    total_amount: float
    status: str
    shipping_address: str
    payment_method: str
    created_at: datetime
    items: list[OrderItemResponse]

    class Config:
        from_attributes = True