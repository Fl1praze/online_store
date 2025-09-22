from app.dao.base import BaseDAO
from app.users.models import Users

class UsersDAO(BaseDAO):
    model = Users

    @classmethod
    async def rotate_password_version(cls, user_id: int) -> int:
        user = await cls.find_by_id(user_id)
        if not user:
            return None
        new_version = user.password_version + 1
        await cls.update(user_id, password_version=new_version)
        return new_version