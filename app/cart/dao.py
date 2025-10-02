from app.dao.base import BaseDAO
from app.cart.models import Cart
from app.cart.models import CartItem

class CartDAO(BaseDAO):
    model = Cart

class CartItemDAO(BaseDAO):
    model = CartItem