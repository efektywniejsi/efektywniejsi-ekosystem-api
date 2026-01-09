import json

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Database Configuration
    DATABASE_URL: str

    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email Configuration
    EMAIL_BACKEND: str = "console"  # "console" or "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@efektywniejsi.pl"
    SMTP_FROM_NAME: str = "Efektywniejsi"

    # Frontend Configuration
    FRONTEND_URL: str = "http://localhost:5173"

    # Password Reset Configuration
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # CORS Configuration
    BACKEND_CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:3000"]'

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Efektywniejsi Ekosystem Auth API"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def cors_origins(self) -> list[str]:
        """
        Parse CORS origins from JSON string to list.

        Returns:
            list[str]: List of allowed CORS origins
        """
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                parsed: list[str] = json.loads(self.BACKEND_CORS_ORIGINS)
                return parsed
            except json.JSONDecodeError:
                return ["http://localhost:5173", "http://localhost:3000"]
        return self.BACKEND_CORS_ORIGINS  # type: ignore[return-value]


# Create global settings instance
settings = Settings()
