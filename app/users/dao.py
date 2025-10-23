from app.dao.base import BaseDAO
from app.users.models import Users
from sqlalchemy.ext.asyncio import AsyncSession

class UsersDAO(BaseDAO):
    model = Users

    @classmethod
    async def rotate_password_version(cls, session: AsyncSession, user_id: int) -> int:
        user = await cls.find_by_id(session, user_id)
        if not user:
            return None
        new_version = user.password_version + 1
        await cls.update(session, user_id, password_version=new_version)
        return new_version