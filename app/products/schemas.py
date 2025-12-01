from pydantic import BaseModel,ConfigDict,Field


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


class ProductList(BaseModel):
    items: list[ResponseProduct] = Field(description="Товары для текущей страницы")
    total: int = Field(ge=0, description="Общее количество товаров")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")
    
    model_config = ConfigDict(from_attributes=True)


class ProductFilter(BaseModel):
    """
    Схема для входящих параметров фильтрации и пагинации.
    """
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(20, ge=1, le=100, description="Размер страницы")
    name: str | None = Field(None, description="Поиск по названию (частичное совпадение, ILIKE)")
    category_id: int | list[int] | None = Field(None, description="ID категории или список ID категорий")
    min_price: float | None = Field(None, ge=0, description="Мин. цена")
    max_price: float | None = Field(None, ge=0, description="Макс. цена")
    in_stock: bool | None = Field(None, description="Только в наличии (true)")