from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    DATABASE_URL: str = None
    SECRET_KEY: str
    ALGORITHM: str

    EMAIL_SENDER: str
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int


    @model_validator(mode='before')
    def get_database_url(cls, values):
        values[
            'DATABASE_URL'] = f'postgresql+asyncpg://{values['DB_USER']}:{values['DB_PASS']}@{values['DB_HOST']}:{values['DB_PORT']}/{values['DB_NAME']}'
        return values

    @property
    def REDIS_URL(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = '.env'

settings = Settings()

