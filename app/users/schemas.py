import re
from typing import Annotated

from pydantic import BaseModel, AfterValidator

NAME_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[ '\-][A-Za-zА-Яа-яЁё]+)*")


def validate_person_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Имя и фамилия не могут быть пустыми")
    if any(ch.isdigit() for ch in v):
        raise ValueError("Имя и фамилия не должны содержать цифры")
    if not NAME_RE.fullmatch(v):
        raise ValueError("Имя и фамилия могут содержать только буквы, пробел, дефис и апостроф")
    return v


def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов, заглавную букву и цифру")
    if not any(ch.isupper() for ch in v):
        raise ValueError("Пароль должен содержать минимум 8 символов, заглавную букву и цифру")
    if not any(ch.isdigit() for ch in v):
        raise ValueError("Пароль должен содержать минимум 8 символов, заглавную букву и цифру")
    return v


PersonName = Annotated[str, AfterValidator(validate_person_name)]
StrongPassword = Annotated[str, AfterValidator(validate_password)]

class CreateUser(BaseModel):
    first_name: PersonName
    last_name: PersonName
    username: str
    email: str
    password: StrongPassword

class LoginUser(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: StrongPassword

class ChangeData(BaseModel):
    first_name: PersonName
    last_name: PersonName
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
    first_name: PersonName | None = None
    last_name: PersonName | None = None
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
