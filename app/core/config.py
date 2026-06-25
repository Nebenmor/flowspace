from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    SECRET_KEY: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    BASE_URL: str
    RESEND_API_KEY: str
    EMAIL_FROM: str
    REDIS_URL: str

    @property
    def async_database_url(self) -> str:
        """
        Render provides a standard postgresql:// connection string.
        SQLAlchemy async requires postgresql+asyncpg://.
        This property handles the conversion automatically in both
        local development and production.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    class Config:
        env_file = ".env"


settings = Settings()