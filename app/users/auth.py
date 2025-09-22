from datetime import datetime, timedelta,timezone
from jose import jwt
from passlib.context import CryptContext
from app.config import settings
from uuid import uuid4


pwd_context = CryptContext(schemes=['bcrypt'],deprecated = 'auto')

def get_password_hash(password: str) ->str:
    return pwd_context.hash(password)

def verify_password(plain_password,hashed_password)->bool:
    return pwd_context.verify(plain_password,hashed_password)


def create_token(
        data: dict,
        expires_delta: timedelta,
        hashed_password: str,
        token_type: str
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    jti = str(uuid4())
    now = datetime.now(timezone.utc)
    to_encode.update({
        'exp':expire,
        'pwd_hash': hashed_password[:8],
        'iat': now,
        'jti': jti,
        'type': token_type
    })
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY,settings.ALGORITHM
    )
    return encoded_jwt

def create_access_token(data: dict, hashed_password: str) -> str:
    return create_token(data, timedelta(minutes=30), hashed_password,"access")

def create_refresh_token(data: dict, hashed_password: str) -> str:
    return create_token(data, timedelta(days=7), hashed_password,"refresh")