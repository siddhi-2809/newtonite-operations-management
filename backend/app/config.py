import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres@localhost:5432/newtonite_db"
    SECRET_KEY: str = "dev-secret-key-for-newtonite-operations-jwt-auth-2026-safe-dev"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"
    
    ADMIN_INITIAL_EMAIL: str = "admin@newtonite.io"
    ADMIN_INITIAL_PASSWORD: str = "AdminSecure123!"
    ADMIN_INITIAL_NAME: str = "System Admin"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
