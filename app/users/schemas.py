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

