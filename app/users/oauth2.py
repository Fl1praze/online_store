from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer


# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



