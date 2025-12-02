from pydantic import BaseModel


class CreateUser(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    password: str

class LoginUser(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ChangeData(BaseModel):
    first_name: str
    last_name: str
    username: str

class UserResponse(BaseModel):
    id: int
    email: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = False
    is_admin: bool = False

    class Config:
        from_attributes = True


class AdminUpdateUser(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
